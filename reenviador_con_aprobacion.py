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
    # Cliente principal (userbot para leer canales)
    client = TelegramClient('reenviador', api_id, api_hash)
    
    # Bot para enviar con botones
    bot = TelegramClient('bot', api_id, api_hash)
    await bot.start(bot_token=bot_token)

    @client.on(events.NewMessage(chats=canales_origen))
    async def nuevo_mensaje(event):
        msg_id = event.message.id
        chat_id = event.chat_id
        
        # Modo automático
        if chat_id in CANALES_AUTOMATICOS:
            texto_limpio = await limpiar_texto(event.message.message)
            texto_final = (texto_limpio + MI_FIRMA) if texto_limpio else ""
            
            if event.message.media:
                await client.send_file(tu_canal, event.message.media, caption=texto_final if texto_final else None)
            elif texto_limpio:
                await client.send_message(tu_canal, texto_final)
            return
        
        # Guardar mensaje
        mensajes_pendientes[msg_id] = {
            'chat_id': chat_id,
            'mensaje': event.message
        }
        
        # Preparar preview
        texto_limpio = await limpiar_texto(event.message.message)
        preview = texto_limpio[:500] if texto_limpio else "📷 Multimedia"
        
        # Botones
        botones = [
            [Button.inline("✅ PUBLICAR", f"pub_{msg_id}")],
            [Button.inline("❌ RECHAZAR", f"del_{msg_id}")]
        ]
        
        # Enviar al bot con botones
        if event.message.media:
            await bot.send_file(mi_chat_id, event.message.media, caption=preview, buttons=botones)
        else:
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
            
            if mensaje_orig.media:
                await client.send_file(tu_canal, mensaje_orig.media, caption=texto_final if texto_final else None)
            elif texto_final:
                await client.send_message(tu_canal, texto_final)
            
            await event.edit("✅ ¡Publicado!")
            del mensajes_pendientes[msg_id]
        
        elif accion == "del":
            await event.edit("❌ Descartado")
            del mensajes_pendientes[msg_id]

await client.start()
print("🚀 Bot activo con botones!")

# Mensaje de prueba
await bot.send_message(mi_chat_id, "✅ Bot iniciado correctamente y conectado!")

await client.run_until_disconnected()

asyncio.run(main())