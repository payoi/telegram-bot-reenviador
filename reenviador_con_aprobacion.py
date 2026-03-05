import asyncio
import os
import re
import json
import base64
from telethon import TelegramClient, events, Button

# ========== VARIABLES DE ENTORNO ==========
api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
mi_chat_id = int(os.getenv('MI_CHAT_ID'))
tu_canal = int(os.getenv('TU_CANAL'))

# ========== CARGAR SESIONES DESDE VARIABLES DE ENTORNO ==========
session_string = os.getenv('SESSION_STRING')
if session_string:
    try:
        session_data = base64.b64decode(session_string)
        with open('reenviador.session', 'wb') as f:
            f.write(session_data)
        print("✅ Sesión de usuario cargada desde variable de entorno")
    except Exception as e:
        print(f"⚠️ Error cargando sesión de usuario: {e}")

bot_session_string = os.getenv('BOT_SESSION_STRING')
if bot_session_string:
    try:
        bot_session_data = base64.b64decode(bot_session_string)
        with open('bot.session', 'wb') as f:
            f.write(bot_session_data)
        print("✅ Sesión del bot cargada desde variable de entorno")
    except Exception as e:
        print(f"⚠️ Error cargando sesión del bot: {e}")
# ================================================================

# Archivos para guardar canales de forma persistente
ARCHIVO_CANALES = 'canales_origen.json'
ARCHIVO_AUTO = 'canales_automaticos.json'

MI_FIRMA = "\n\n📢 Únete: @NotiGlobalVE"

mensajes_pendientes = {}
stats = {'aprobados': 0, 'rechazados': 0}

# ========== FUNCIONES PARA GESTIONAR CANALES ==========
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
# ======================================================

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

    # ========== COMANDOS BÁSICOS ==========
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def cmd_start(event):
        if event.chat_id != mi_chat_id:
            return
        await event.reply(
            "🤖 **Bot de Reenvío Activo v2.0**\n\n"
            "**📋 Comandos básicos:**\n"
            "• `/test` - Probar conexión\n"
            "• `/canales` - Ver canales monitoreados\n"
            "• `/ultimos` - Ver últimos mensajes\n"
            "• `/buscar [texto]` - Buscar en canales\n"
            "• `/pendientes` - Mensajes pendientes\n"
            "• `/stats` - Estadísticas\n\n"
            "**⚙️ Gestión de canales:**\n"
            "• `/agregar [ID]` - Agregar canal origen\n"
            "• `/quitar [ID]` - Quitar canal origen\n"
            "• `/lista` - Ver configuración completa\n\n"
            "**🔄 Canales automáticos:**\n"
            "• `/auto_agregar [ID]` - Publicar sin aprobación\n"
            "• `/auto_quitar [ID]` - Requiere aprobación\n\n"
            "💡 **Ejemplo:**\n"
            "`/agregar -1001234567890`"
        )

    @bot.on(events.NewMessage(pattern='/test'))
    async def cmd_test(event):
        if event.chat_id != mi_chat_id:
            return
        await event.reply(
            f"✅ **Bot funcionando correctamente**\n\n"
            f"📡 Canales: {len(canales_origen)}\n"
            f"🔄 Automáticos: {len(CANALES_AUTOMATICOS)}\n"
            f"📬 Pendientes: {len(mensajes_pendientes)}"
        )

    @bot.on(events.NewMessage(pattern='/stats'))
    async def cmd_stats(event):
        if event.chat_id != mi_chat_id:
            return
        await event.reply(
            f"📊 **Estadísticas del Bot**\n\n"
            f"✅ Aprobados: {stats['aprobados']}\n"
            f"❌ Rechazados: {stats['rechazados']}\n"
            f"📬 Pendientes: {len(mensajes_pendientes)}\n"
            f"📡 Canales monitoreados: {len(canales_origen)}\n"
            f"🔄 Canales automáticos: {len(CANALES_AUTOMATICOS)}"
        )

    @bot.on(events.NewMessage(pattern='/pendientes'))
    async def cmd_pendientes(event):
        if event.chat_id != mi_chat_id:
            return
        cantidad = len(mensajes_pendientes)
        if cantidad == 0:
            await event.reply("📭 No hay mensajes pendientes")
        else:
            await event.reply(f"📬 Tienes **{cantidad}** mensaje(s) pendiente(s)")

    # ========== GESTIÓN DE CANALES ==========

    @bot.on(events.NewMessage(pattern='/canales'))
    async def cmd_canales(event):
        if event.chat_id != mi_chat_id:
            return
        
        if not canales_origen:
            await event.reply(
                "📝 **No hay canales configurados**\n\n"
                "Usa `/agregar -1001234567890` para agregar uno.\n\n"
                "💡 Para obtener IDs de canales, reenvía un mensaje del canal a @userinfobot"
            )
            return
        
        texto = "📡 **Canales monitoreados:**\n\n"
        for i, canal_id in enumerate(canales_origen, 1):
            try:
                canal = await client.get_entity(canal_id)
                nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
                auto = " 🔄 (AUTO)" if canal_id in CANALES_AUTOMATICOS else ""
                texto += f"{i}. **{nombre}**{auto}\n   `{canal_id}`\n\n"
            except:
                texto += f"{i}. `{canal_id}` ⚠️ (no accesible)\n\n"
        
        texto += f"💡 Total: {len(canales_origen)} canales"
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
            
            # Verificar acceso al canal
            try:
                canal = await client.get_entity(canal_id)
                nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
            except Exception as e:
                await event.reply(
                    f"❌ **No puedo acceder a ese canal**\n\n"
                    f"Error: {str(e)}\n\n"
                    f"💡 Asegúrate de que tu cuenta esté unida al canal."
                )
                return
            
            # Agregar si no existe
            if canal_id not in canales_origen:
                canales_origen.append(canal_id)
                guardar_canales(canales_origen)
                await event.reply(
                    f"✅ **Canal agregado exitosamente**\n\n"
                    f"📢 Nombre: **{nombre}**\n"
                    f"🆔 ID: `{canal_id}`\n\n"
                    f"Los mensajes nuevos requerirán aprobación.\n"
                    f"Usa `/auto_agregar {canal_id}` para publicar automáticamente."
                )
            else:
                await event.reply(f"⚠️ El canal **{nombre}** ya está en la lista")
            
        except Exception as e:
            await event.reply(
                f"❌ **Error al agregar canal**\n\n"
                f"{str(e)}\n\n"
                f"💡 **Uso correcto:**\n"
                f"`/agregar -1001234567890`\n"
                f"`/agregar @username`"
            )

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
                
                await event.reply(
                    f"✅ **Canal eliminado**\n\n"
                    f"🆔 ID: `{canal_id}`\n\n"
                    f"Ya no se monitorearán mensajes de este canal."
                )
            else:
                await event.reply(
                    f"⚠️ **El canal `{canal_id}` no está en la lista**\n\n"
                    f"Usa `/canales` para ver los canales activos."
                )
            
        except Exception as e:
            await event.reply(
                f"❌ **Error**\n\n"
                f"{str(e)}\n\n"
                f"💡 Uso: `/quitar -1001234567890`"
            )

    @bot.on(events.NewMessage(pattern=r'/auto_agregar (-?\d+)'))
    async def cmd_auto_agregar(event):
        if event.chat_id != mi_chat_id:
            return
        
        try:
            canal_id = int(event.pattern_match.group(1))
            
            if canal_id not in canales_origen:
                await event.reply(
                    f"⚠️ **Primero debes agregar el canal**\n\n"
                    f"Usa: `/agregar {canal_id}`"
                )
                return
            
            if canal_id not in CANALES_AUTOMATICOS:
                CANALES_AUTOMATICOS.append(canal_id)
                guardar_canales_auto(CANALES_AUTOMATICOS)
                
                try:
                    canal = await client.get_entity(canal_id)
                    nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
                except:
                    nombre = str(canal_id)
                
                await event.reply(
                    f"✅ **Canal configurado como AUTOMÁTICO**\n\n"
                    f"📢 {nombre}\n"
                    f"🆔 `{canal_id}`\n\n"
                    f"🔄 Los mensajes se publicarán sin aprobación."
                )
            else:
                await event.reply("⚠️ Este canal ya está en modo automático")
            
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
                
                try:
                    canal = await client.get_entity(canal_id)
                    nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
                except:
                    nombre = str(canal_id)
                
                await event.reply(
                    f"✅ **Canal quitado de automáticos**\n\n"
                    f"📢 {nombre}\n"
                    f"🆔 `{canal_id}`\n\n"
                    f"Ahora los mensajes requerirán aprobación manual."
                )
            else:
                await event.reply("⚠️ Este canal no está en modo automático")
            
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}")

    @bot.on(events.NewMessage(pattern='/lista'))
    async def cmd_lista(event):
        if event.chat_id != mi_chat_id:
            return
        
        if not canales_origen:
            await event.reply(
                "📝 **No hay canales configurados**\n\n"
                "Usa `/start` para ver los comandos disponibles."
            )
            return
        
        texto = "📋 **Configuración completa del bot:**\n\n"
        
        # Canales con aprobación manual
        canales_manuales = [c for c in canales_origen if c not in CANALES_AUTOMATICOS]
        if canales_manuales:
            texto += "**✋ Canales con aprobación manual:**\n"
            for canal_id in canales_manuales:
                try:
                    canal = await client.get_entity(canal_id)
                    nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
                    texto += f"• **{nombre}**\n  `{canal_id}`\n"
                except:
                    texto += f"• `{canal_id}` ⚠️\n"
            texto += "\n"
        
        # Canales automáticos
        if CANALES_AUTOMATICOS:
            texto += "**🔄 Canales automáticos:**\n"
            for canal_id in CANALES_AUTOMATICOS:
                try:
                    canal = await client.get_entity(canal_id)
                    nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
                    texto += f"• **{nombre}**\n  `{canal_id}`\n"
                except:
                    texto += f"• `{canal_id}` ⚠️\n"
            texto += "\n"
        
        texto += f"━━━━━━━━━━━━━━━━\n"
        texto += f"📊 **Resumen:**\n"
        texto += f"• Total canales: {len(canales_origen)}\n"
        texto += f"• Automáticos: {len(CANALES_AUTOMATICOS)}\n"
        texto += f"• Con aprobación: {len(canales_manuales)}\n"
        texto += f"• Pendientes: {len(mensajes_pendientes)}"
        
        await event.reply(texto)

    # ========== BÚSQUEDA Y ÚLTIMOS MENSAJES ==========

    @bot.on(events.NewMessage(pattern='/ultimos'))
    async def cmd_ultimos(event):
        if event.chat_id != mi_chat_id:
            return
        
        if not canales_origen:
            await event.reply("⚠️ No hay canales configurados")
            return
        
        await event.reply("🔍 Buscando últimos mensajes...")
        
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
            except Exception as e:
                await bot.send_message(mi_chat_id, f"❌ Error en canal {canal_id}: {str(e)}")
        
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
            await event.reply(f"❌ No se encontró: **{palabra}**")
        else:
            await event.reply(f"✅ Encontrados: **{encontrados}** resultados")

    # ========== MONITOREO DE MENSAJES NUEVOS ==========

    @client.on(events.NewMessage(chats=lambda chat_id: chat_id in canales_origen))
    async def nuevo_mensaje(event):
        msg_id = event.message.id
        chat_id = event.chat_id
        
        # Canales automáticos (publicar sin aprobación)
        if chat_id in CANALES_AUTOMATICOS:
            texto_limpio = await limpiar_texto(event.message.message)
            texto_final = (texto_limpio + MI_FIRMA) if texto_limpio else ""
            
            try:
                if event.message.media:
                    await client.send_file(tu_canal, event.message.media, caption=texto_final if texto_final else None)
                elif texto_limpio:
                    await client.send_message(tu_canal, texto_final)
            except Exception as e:
                await bot.send_message(mi_chat_id, f"❌ Error publicando automáticamente: {str(e)}")
            return
        
        # Canales con aprobación manual
        mensajes_pendientes[msg_id] = {'chat_id': chat_id, 'mensaje': event.message}
        texto_limpio = await limpiar_texto(event.message.message)
        preview = texto_limpio[:500] if texto_limpio else "📷 Multimedia"
        
        botones = [
            [Button.inline("✅ PUBLICAR", f"pub_{msg_id}")],
            [Button.inline("❌ RECHAZAR", f"del_{msg_id}")]
        ]
        
        try:
            # Obtener nombre del canal
            try:
                canal = await client.get_entity(chat_id)
                canal_nombre = canal.title if hasattr(canal, 'title') else str(chat_id)
            except:
                canal_nombre = str(chat_id)
            
            await bot.send_message(mi_chat_id, f"📢 **Nuevo mensaje de:** {canal_nombre}")
            
            if event.message.media:
                await bot.send_file(mi_chat_id, event.message.media, caption=preview, buttons=botones)
            else:
                await bot.send_message(mi_chat_id, preview, buttons=botones)
        except Exception as e:
            await bot.send_message(mi_chat_id, f"⚠️ Error: {str(e)}\n\n{preview}", buttons=botones)

    # ========== BOTONES DE APROBACIÓN/RECHAZO ==========

    @bot.on(events.CallbackQuery)
    async def callback(event):
        data = event.data.decode()
        accion, msg_id = data.split('_')
        msg_id = int(msg_id)
        
        if msg_id not in mensajes_pendientes:
            await event.answer("⚠️ Mensaje expirado o ya procesado", alert=True)
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
                
                await event.edit("✅ ¡Publicado en tu canal!")
                stats['aprobados'] += 1
            except Exception as e:
                await event.edit(f"❌ Error al publicar: {str(e)}")
            
            del mensajes_pendientes[msg_id]
        
        elif accion == "del":
            await event.edit("❌ Mensaje descartado")
            stats['rechazados'] += 1
            del mensajes_pendientes[msg_id]

    # ========== INICIO DEL BOT ==========

    await client.start()
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("🚀 Bot de Reenvío Activo v2.0")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📊 Canales monitoreados: {len(canales_origen)}")
    print(f"🔄 Canales automáticos: {len(CANALES_AUTOMATICOS)}")
    
    if canales_origen:
        print("\n📡 Canales activos:")
        for canal_id in canales_origen:
            try:
                canal = await client.get_entity(canal_id)
                nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
                auto = " [AUTO]" if canal_id in CANALES_AUTOMATICOS else ""
                print(f"  • {nombre}{auto}")
            except:
                print(f"  • {canal_id}")
    else:
        print("\n⚠️ No hay canales configurados")
        print("💡 Envía /agregar [ID] para agregar canales")
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    await bot.send_message(
        mi_chat_id,
        f"✅ **Bot iniciado correctamente**\n\n"
        f"📡 Canales: {len(canales_origen)}\n"
        f"🔄 Automáticos: {len(CANALES_AUTOMATICOS)}\n\n"
        f"Usa `/start` para ver todos los comandos disponibles."
    )
    
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())