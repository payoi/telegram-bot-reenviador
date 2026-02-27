import asyncio
import os
import re
from telethon import TelegramClient, events, Button

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
bot_token = os.getenv('BOT_TOKEN')
mi_chat_id = int(os.getenv('MI_CHAT_ID'))
tu_canal = int(os.getenv('TU_CANAL'))
canales_origen = [int(x.strip()) for x in os.getenv('CANALES_ORIGEN').split(',')]

MI_FIRMA = "\n\n🔔 Únete: @NotiGlobalVE"

auto_env = os.getenv('CANALES_AUTOMATICOS', '')
CANALES_AUTOMATICOS = [int(x.strip()) for x in auto_env.split(',') if x.strip()] if auto_env else []

mensajes_pendientes = {}
stats = {'aprobados': 0, 'rechazados': 0}

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

    # ==================== COMANDOS ====================
    
    @bot.on(events.NewMessage(pattern='/start'))
    async def cmd_start(event):
        if event.chat_id != mi_chat_id:
            return
        await event.reply(
            "🤖 **Bot de Reenvío Activo**\n\n"
            "**Comandos disponibles:**\n"
            "/buscar [texto] - Buscar en canales\n"
            "/ultimos - Ver últimos 5 mensajes\n"
            "/canales - Ver canales monitoreados\n"
            "/pendientes - Ver mensajes pendientes\n"
            "/stats - Ver estadísticas\n"
            "/test - Probar conexión"
        )

    @bot.on(events.NewMessage(pattern='/test'))
    async def cmd_test(event):
        if event.chat_id != mi_chat_id:
            return
        await event.reply("✅ Bot funcionando correctamente!")

    @bot.on(events.NewMessage(pattern='/canales'))
    async def cmd_canales(event):
        if event.chat_id != mi_chat_id:
            return
        
        texto = "📡 **Canales monitoreados:**\n\n"
        for i, canal_id in enumerate(canales_origen, 1):
            try:
                canal = await client.get_entity(canal_id)
                nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
                texto += f"{i}. {nombre}\n"
            except:
                texto += f"{i}. ID: {canal_id}\n"
        
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
            f"📬 Pendientes: {len(mensajes_pendientes)}"
        )

@bot.on(events.NewMessage(pattern='/ultimos'))
async def cmd_ultimos(event):
    if event.chat_id != mi_chat_id:
        return
    
    await event.reply("🔍 Buscando últimos mensajes...")
    
    for canal_id in canales_origen:
        try:
            canal = await client.get_entity(canal_id)
            nombre = canal.title if hasattr(canal, 'title') else str(canal_id)
            
            await bot.send_message(mi_chat_id, f"📢 **{nombre}:**")
            
            async for msg in client.iter_messages(canal_id, limit=3):
                texto_limpio = await limpiar_texto(msg.message) if msg.message else ""
                preview = texto_limpio[:800] if texto_limpio else "📷 Multimedia"
                
                mensajes_pendientes[msg.id] = {
                    'chat_id': canal_id,
                    'mensaje': msg
                }
                
                botones = [
                    [Button.inline("✅ PUBLICAR", f"pub_{msg.id}")],
                    [Button.inline("❌ RECHAZAR", f"del_{msg.id}")]
                ]
                
                if msg.media:
                    await bot.send_file(mi_chat_id, msg.media, caption=preview, buttons=botones)
                else:
                    await bot.send_message(mi_chat_id, preview, buttons=botones)
                
                await asyncio.sleep(0.5)  # Evitar flood
                
        except Exception as e:
            await bot.send_message(mi_chat_id, f"❌ Error: {e}")
    
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
                    if msg.message and encontrados < 5:
                        texto_limpio = await limpiar_texto(msg.message)
                        preview = texto_limpio[:300] if texto_limpio else "📷 Multimedia"
                        
                        mensajes_pendientes[msg.id] = {
                            'chat_id': canal_id,
                            'mensaje': msg
                        }
                        
                        botones = [
                            [Button.inline("✅ PUBLICAR", f"pub_{msg.id}")],
                            [Button.inline("❌ RECHAZAR", f"del_{msg.id}")]
                        ]
                        
                        if msg.media:
                            await bot.send_file(mi_chat_id, msg.media, caption=preview, buttons=botones)
                        else:
                            await bot.send_message(mi_chat_id, preview, buttons=botones)
                        
                        encontrados += 1
            except:
                pass
        
        if encontrados == 0:
            await event.reply(f"❌ No se encontró: {palabra}")
        else:
            await event.reply(f"✅ Encontrados: {encontrados} mensaje(s)")

    # ==================== EVENTOS DE CANALES ====================

    @client.on(events.NewMessage(chats=canales_origen))
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
        
        mensajes_pendientes[msg_id] = {
            'chat_id': chat_id,
            'mensaje': event.message
        }
        
        texto_limpio = await limpiar_texto(event.message.message)
        preview = texto_limpio[:500] if texto_limpio else "📷 Multimedia"
        
        botones = [
            [Button.inline("✅ PUBLICAR", f"pub_{msg_id}")],
            [Button.inline("❌ RECHAZAR", f"del_{msg_id}")]
        ]
        
        if event.message.media:
            await bot.send_file(mi_chat_id, event.message.media, caption=preview, buttons=botones)
        else:
            await bot.send_message(mi_chat_id, preview, buttons=botones)

    # ==================== BOTONES ====================

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
            
            if mensaje_orig.media:
                await client.send_file(tu_canal, mensaje_orig.media, caption=texto_final if texto_final else None)
            elif texto_final:
                await client.send_message(tu_canal, texto_final)
            
            await event.edit("✅ ¡Publicado!")
            stats['aprobados'] += 1
            del mensajes_pendientes[msg_id]
        
        elif accion == "del":
            await event.edit("❌ Descartado")
            stats['rechazados'] += 1
            del mensajes_pendientes[msg_id]

    await client.start()
    print("🚀 Bot activo con botones y comandos!")
    
    await bot.send_message(mi_chat_id, "✅ Bot iniciado correctamente!")
    
    await client.run_until_disconnected()

asyncio.run(main())