import asyncio
import os
import re
import json
from telethon import TelegramClient, events, Button

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
mi_chat_id = int(os.getenv('MI_CHAT_ID'))
tu_canal = int(os.getenv('TU_CANAL'))

# Archivo para guardar canales de forma persistente
ARCHIVO_CANALES = 'canales_origen.json'
ARCHIVO_AUTO = 'canales_automaticos.json'

MI_FIRMA = "\n\n📢 Únete: @NotiGlobalVE"

mensajes_pendientes = {}
stats = {'aprobados': 0, 'rechazados': 0}

# Funciones para gestionar canales
def cargar_canales():
    if os.path.exists(ARCHIVO_CANALES):
        with open(ARCHIVO_CANALES, 'r') as f:
            return json.load(f)
    # Si no existe, carga desde variable de entorno (migración inicial)
    canales_env = os.getenv('CANALES_ORIGEN', '')
    return [int(x.strip()) for x in canales_env.split(',') if x.strip()]

def guardar_canales(canales):
    with open(ARCHIVO_CANALES, 'w') as f:
        json.dump(canales, f, indent=2)

def cargar_canales_auto():
    if os.path.exists(ARCHIVO_AUTO):
        with open(ARCHIVO_AUTO, 'r') as f:
            return json.load(f)
    auto_env = os.getenv('CANALES_AUTOMATICOS', '')
    return [int(x.strip()) for x in auto_env.split(',') if x.strip()] if auto_env else []

def guardar_canales_auto(canales):
    with open(ARCHIVO_AUTO, 'w') as f:
        json.dump(canales, f, indent=2)

canales_origen = cargar_canales()
CANALES_AUTOMATICOS = cargar_canales_auto()

async def limpiar_texto(texto):
    if not texto:
        return ""
    texto = re.sub(r'@\w+', '', texto)
    texto = re.sub(r'https?://\S+', '', texto)
    texto = re.sub(r'www\.\S+', '', texto)
    texto = re.sub(r't\.me/\S+', '', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    texto = re.sub(r'  +', ' ', texto)
    return texto.strip()

async def main():
    client = TelegramClient('reenviador', api_id, api_hash)
    bot = TelegramClient('bot', api_id, api_hash)
    await bot.start(bot_token=bot_token)

    @bot.on(events.NewMessage(pattern='/start'))
    async def cmd_start(event):
        if event.chat_id != mi_chat_id:
            return
        await event.reply(
            "🤖 **Bot de Reenvío Activo**\n\n"
            "**Comandos básicos:**\n"
            "/test - Probar conexión\n"
            "/canales - Ver canales\n"
            "/ultimos - Últimos mensajes\n"
            "/buscar [texto] - Buscar\n"
            "/pendientes - Mensajes pendientes\n"
            "/stats - Estadísticas\n\n"
            "**Gestión de canales:**\n"
            "/agregar [ID] - Agregar canal origen\n"
            "/quitar [ID] - Quitar canal origen\n"
            "/auto_agregar [ID] - Canal automático\n"
            "/auto_quitar [ID] - Quitar de automáticos\n"
            "/lista - Ver todos los canales"
        )

    @bot.on(events.NewMessage(pattern='/test'))
    async def cmd_test(event):
        if event.chat_id != mi_chat_id:
            return
        await event.reply("✅ Bot funcionando!")

    @bot.on(events.NewMessage(pattern='/canales'))
    async def cmd_canales(event):
        if event.chat_id != mi_chat_id:
            return
        if not canales_origen:
            await event.reply("📝 No hay canales configurados.\n\nUsa /agregar [ID] para agregar uno.")
            return
        
        texto = "📡 **Canales monitoreados:**\n\n"
        for i, canal_id in enumerate(canales_origen, 1):
            try:
                canal = await client.get_entity(canal_id)
                nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
                auto = " 🔄 (AUTO)" if canal_id in CANALES_AUTOMATICOS else ""
                texto += f"{i}. **{nombre}**{auto}\n   ID: `{canal_id}`\n\n"
            except:
                texto += f"{i}. ID: `{canal_id}`\n\n"
        await event.reply(texto)

    @bot.on(events.NewMessage(pattern=r'/agregar (-?\d+|@\w+)'))
    async def cmd_agregar(event):
        if event.chat_id != mi_chat_id:
            return
        
        canal_input = event.pattern_match.group(1)
        
        try:
            # Convertir a int si es ID numérico
            try:
                canal_id = int(canal_input)
            except:
                # Es username, obtener el ID
                canal_entity = await client.get_entity(canal_input)
                canal_id = canal_entity.id
            
            # Verificar acceso
            try:
                canal = await client.get_entity(canal_id)
                nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
            except Exception as e:
                await event.reply(f"❌ No puedo acceder a ese canal.\n{str(e)}")
                return
            
            # Agregar si no existe
            if canal_id not in canales_origen:
                canales_origen.append(canal_id)
                guardar_canales(canales_origen)
                await event.reply(f"✅ Canal agregado:\n**{nombre}**\nID: `{canal_id}`")
            else:
                await event.reply("⚠️ Ese canal ya está en la lista")
        
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}\n\nUso: /agregar -1001234567890 o /agregar @username")

    @bot.on(events.NewMessage(pattern=r'/quitar (-?\d+)'))
    async def cmd_quitar(event):
        if event.chat_id != mi_chat_id:
            return
        
        try:
            canal_id = int(event.pattern_match.group(1))
            
            if canal_id in canales_origen:
                canales_origen.remove(canal_id)
                guardar_canales(canales_origen)
                
                # También quitarlo de automáticos si estaba
                if canal_id in CANALES_AUTOMATICOS:
                    CANALES_AUTOMATICOS.remove(canal_id)
                    guardar_canales_auto(CANALES_AUTOMATICOS)
                
                await event.reply(f"✅ Canal eliminado: `{canal_id}`")
            else:
                await event.reply("⚠️ Ese canal no está en la lista")
        
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}\n\nUso: /quitar -1001234567890")

    @bot.on(events.NewMessage(pattern=r'/auto_agregar (-?\d+)'))
    async def cmd_auto_agregar(event):
        if event.chat_id != mi_chat_id:
            return
        
        try:
            canal_id = int(event.pattern_match.group(1))
            
            if canal_id not in canales_origen:
                await event.reply("⚠️ Primero agrégalo con /agregar")
                return
            
            if canal_id not in CANALES_AUTOMATICOS:
                CANALES_AUTOMATICOS.append(canal_id)
                guardar_canales_auto(CANALES_AUTOMATICOS)
                await event.reply(f"✅ Canal configurado como AUTOMÁTICO: `{canal_id}`\n\nLos mensajes se publicarán sin aprobación.")
            else:
                await event.reply("⚠️ Ya está en modo automático")
        
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}")

    @bot.on(events.NewMessage(pattern=r'/auto_quitar (-?\d+)'))
    async def cmd_auto_quitar(event):
        if event.chat_id != mi_chat_id:
            return
        
        try:
            canal_id = int(event.pattern_match.group(1))
            
            if canal_id in CANALES_AUTOMATICOS:
                CANALES_AUTOMATICOS.remove(canal_id)
                guardar_canales_auto(CANALES_AUTOMATICOS)
                await event.reply(f"✅ Canal quitado de automáticos: `{canal_id}`\n\nAhora requerirá aprobación manual.")
            else:
                await event.reply("⚠️ Ese canal no está en automáticos")
        
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}")

    @bot.on(events.NewMessage(pattern='/lista'))
    async def cmd_lista(event):
        if event.chat_id != mi_chat_id:
            return
        
        if not canales_origen and not CANALES_AUTOMATICOS:
            await event.reply("📝 No hay canales configurados.")
            return
        
        texto = "📋 **Configuración actual:**\n\n"
        
        if canales_origen:
            texto += "**📡 Canales con aprobación:**\n"
            for canal_id in canales_origen:
                if canal_id not in CANALES_AUTOMATICOS:
                    try:
                        canal = await client.get_entity(canal_id)
                        nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
                        texto += f"• **{nombre}**\n  `{canal_id}`\n"
                    except:
                        texto += f"• `{canal_id}`\n"
            texto += "\n"
        
        if CANALES_AUTOMATICOS:
            texto += "**🔄 Canales automáticos:**\n"
            for canal_id in CANALES_AUTOMATICOS:
                try:
                    canal = await client.get_entity(canal_id)
                    nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
                    texto += f"• **{nombre}**\n  `{canal_id}`\n"
                except:
                    texto += f"• `{canal_id}`\n"
        
        texto += f"\n💡 Total: {len(canales_origen)} canales"
        await event.reply(texto)

    @bot.on(events.NewMessage(pattern='/pendientes'))
    async def cmd_pendientes(event):
        if event.chat_id != mi_chat_id:
            return
        cantidad = len(mensajes_pendientes)
        if cantidad == 0:
            await event.reply("📭 No hay mensajes pendientes")
        else:
            await event.reply(f"📬 Tienes **{cantidad}** mensaje(s) pendiente(s)")

    @bot.on(events.NewMessage(pattern='/stats'))
    async def cmd_stats(event):
        if event.chat_id != mi_chat_id:
            return
        await event.reply(
            f"📊 **Estadísticas:**\n\n"
            f"✅ Aprobados: {stats['aprobados']}\n"
            f"❌ Rechazados: {stats['rechazados']}\n"
            f"📬 Pendientes: {len(mensajes_pendientes)}\n"
            f"📡 Canales: {len(canales_origen)}\n"
            f"🔄 Automáticos: {len(CANALES_AUTOMATICOS)}"
        )

    @bot.on(events.NewMessage(pattern='/ultimos'))
    async def cmd_ultimos(event):
        if event.chat_id != mi_chat_id:
            return
        
        if not canales_origen:
            await event.reply("⚠️ No hay canales configurados")
            return
        
        await event.reply("🔍 Buscando...")
        for canal_id in canales_origen:
            try:
                canal = await client.get_entity(canal_id)
                nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
                await bot.send_message(mi_chat_id, f"📢 **{nombre}:**")
                async for msg in client.iter_messages(canal_id, limit=3):
                    try:
                        texto_limpio = await limpiar_texto(msg.message) if msg.message else ""
                        preview = texto_limpio[:800] if texto_limpio else "📷 Multimedia"
                        mensajes_pendientes[msg.id] = {'chat_id': canal_id, 'mensaje': msg}
                        botones = [
                            [Button.inline("✅ PUBLICAR", f"pub_{msg.id}")],
                            [Button.inline("❌ RECHAZAR", f"del_{msg.id}")]
                        ]
                        if msg.media:
                            try:
                                await bot.send_file(mi_chat_id, msg.media, caption=preview, buttons=botones)
                            except:
                                await bot.send_message(mi_chat_id, preview + "\n\n⚠️ (Multimedia no disponible)", buttons=botones)
                        else:
                            await bot.send_message(mi_chat_id, preview, buttons=botones)
                        await asyncio.sleep(0.5)
                    except:
                        pass
            except:
                pass
        await bot.send_message(mi_chat_id, "✅ Listo!")

    @bot.on(events.NewMessage(pattern=r'/buscar (.+)'))
    async def cmd_buscar(event):
        if event.chat_id != mi_chat_id:
            return
        palabra = event.pattern_match.group(1)
        await event.reply(f"🔍 Buscando: **{palabra}**...")
        encontrados = 0
        for canal_id in canales_origen:
            try:
                async for msg in client.iter_messages(canal_id, limit=20, search=palabra):
                    if encontrados < 5:
                        try:
                            texto_limpio = await limpiar_texto(msg.message) if msg.message else ""
                            preview = texto_limpio[:500] if texto_limpio else "📷 Multimedia"
                            mensajes_pendientes[msg.id] = {'chat_id': canal_id, 'mensaje': msg}
                            botones = [
                                [Button.inline("✅ PUBLICAR", f"pub_{msg.id}")],
                                [Button.inline("❌ RECHAZAR", f"del_{msg.id}")]
                            ]
                            if msg.media:
                                try:
                                    await bot.send_file(mi_chat_id, msg.media, caption=preview, buttons=botones)
                                except:
                                    await bot.send_message(mi_chat_id, preview, buttons=botones)
                            else:
                                await bot.send_message(mi_chat_id, preview, buttons=botones)
                            encontrados += 1
                            await asyncio.sleep(0.5)
                        except:
                            pass
            except:
                pass
        if encontrados == 0:
            await event.reply(f"❌ No se encontró: {palabra}")
        else:
            await event.reply(f"✅ Encontrados: {encontrados}")

    # IMPORTANTE: Actualizar el listener dinámicamente
    async def actualizar_listener():
        # Esta función ya no es necesaria porque usamos la lista global canales_origen
        pass

    @client.on(events.NewMessage(chats=lambda chat_id: chat_id in canales_origen))
    async def nuevo_mensaje(event):
        msg_id = event.message.id
        chat_id = event.chat_id
        
        if chat_id in CANALES_AUTOMATICOS:
            texto_limpio = await limpiar_texto(event.message.message)
            texto_final = (texto_limpio + MI_FIRMA) if texto_limpio else ""
            if event.message.media:
                await client.send_file(tu_canal, event.message.media, caption=texto_final if texto_final else None)
            elif texto_limpio:
                await client.send_message(tu_canal, texto_final)
            return
        
        mensajes_pendientes[msg_id] = {'chat_id': chat_id, 'mensaje': event.message}
        texto_limpio = await limpiar_texto(event.message.message)
        preview = texto_limpio[:500] if texto_limpio else "📷 Multimedia"
        botones = [
            [Button.inline("✅ PUBLICAR", f"pub_{msg_id}")],
            [Button.inline("❌ RECHAZAR", f"del_{msg_id}")]
        ]
        try:
            if event.message.media:
                await bot.send_file(mi_chat_id, event.message.media, caption=preview, buttons=botones)
            else:
                await bot.send_message(mi_chat_id, preview, buttons=botones)
        except:
            await bot.send_message(mi_chat_id, preview, buttons=botones)

    @bot.on(events.CallbackQuery)
    async def callback(event):
        data = event.data.decode()
        accion, msg_id = data.split('_')
        msg_id = int(msg_id)
        if msg_id not in mensajes_pendientes:
            await event.answer("⚠️ Mensaje expirado", alert=True)
            return
        mensaje_orig = mensajes_pendientes[msg_id]['mensaje']
        if accion == "pub":
            texto_limpio = await limpiar_texto(mensaje_orig.message)
            texto_final = (texto_limpio + MI_FIRMA) if texto_limpio else ""
            try:
                if mensaje_orig.media:
                    await client.send_file(tu_canal, mensaje_orig.media, caption=texto_final if texto_final else None)
                elif texto_final:
                    await client.send_message(tu_canal, texto_final)
                await event.edit("✅ ¡Publicado!")
                stats['aprobados'] += 1
            except Exception as e:
                await event.edit(f"❌ Error: {e}")
            del mensajes_pendientes[msg_id]
        elif accion == "del":
            await event.edit("❌ Descartado")
            stats['rechazados'] += 1
            del mensajes_pendientes[msg_id]

    await client.start()
    print(f"🚀 Bot activo!")
    print(f"📊 Canales monitoreados: {len(canales_origen)}")
    print(f"🔄 Canales automáticos: {len(CANALES_AUTOMATICOS)}")
    await bot.send_message(mi_chat_id, 
        f"✅ **Bot iniciado!**\n\n"
        f"📡 Canales: {len(canales_origen)}\n"
        f"🔄 Automáticos: {len(CANALES_AUTOMATICOS)}\n\n"
        f"Usa /start para ver comandos"
    )
    await client.run_until_disconnected()

asyncio.run(main())