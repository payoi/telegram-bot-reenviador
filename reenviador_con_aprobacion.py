import asyncio
import os
import re
from telethon import TelegramClient, events

api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
tu_canal = int(os.getenv('TU_CANAL'))
canales_origen = [int(x.strip()) for x in os.getenv('CANALES_ORIGEN').split(',')]

MI_FIRMA = "\n\n🔔 Únete: @NotiGlobalVE"

auto_env = os.getenv('CANALES_AUTOMATICOS', '')
CANALES_AUTOMATICOS = [int(x.strip()) for x in auto_env.split(',') if x.strip()] if auto_env else []

mensajes_pendientes = {}
ultimo_msg_id = None

async def limpiar_texto(texto):
    if not texto:
        return texto
    texto = re.sub(r'@\w+', '', texto)
    texto = re.sub(r'https?://t\.me/\S+', '', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()

async def main():
    global ultimo_msg_id
    client = TelegramClient('reenviador', api_id, api_hash)

    @client.on(events.NewMessage(chats=canales_origen))
    async def nuevo_mensaje(event):
        global ultimo_msg_id
        
        # Aceptar mensajes con o sin texto
        msg_id = event.message.id
        chat_id = event.chat_id
        
        # Modo automático
        if chat_id in CANALES_AUTOMATICOS:
            texto_limpio = await limpiar_texto(event.message.message) if event.message.message else ""
            texto_final = (texto_limpio + MI_FIRMA) if texto_limpio else MI_FIRMA
            
            if event.message.media:
                await client.send_file(
                    tu_canal, 
                    event.message.media,
                    caption=texto_final if texto_final.strip() != MI_FIRMA.strip() else None
                )
            elif texto_limpio:
                await client.send_message(tu_canal, texto_final)
            return
        
        # Guardar mensaje
        mensajes_pendientes[msg_id] = {'chat_id': chat_id, 'mensaje': event.message}
        ultimo_msg_id = msg_id
        
        # Reenviar el mensaje completo con multimedia
        await client.forward_messages('me', event.message)

    @client.on(events.NewMessage(chats='me', outgoing=True))
    async def respuesta_usuario(event):
        global ultimo_msg_id
        texto = event.message.message.strip().lower()
        
        if texto in ['si', 's', 'ok', '1']:
            if not ultimo_msg_id or ultimo_msg_id not in mensajes_pendientes:
                return
            
            msg_data = mensajes_pendientes[ultimo_msg_id]
            mensaje_orig = msg_data['mensaje']
            
            texto_limpio = await limpiar_texto(mensaje_orig.message) if mensaje_orig.message else ""
            texto_final = (texto_limpio + MI_FIRMA) if texto_limpio else MI_FIRMA
            
            if mensaje_orig.media:
                await client.send_file(
                    tu_canal,
                    mensaje_orig.media,
                    caption=texto_final if texto_final.strip() != MI_FIRMA.strip() else None
                )
            elif texto_limpio:
                await client.send_message(tu_canal, texto_final)
            
            await event.reply("✅ Publicado!")
            del mensajes_pendientes[ultimo_msg_id]
            ultimo_msg_id = None
            
        elif texto in ['no', 'n', '0']:
            if ultimo_msg_id and ultimo_msg_id in mensajes_pendientes:
                await event.reply("❌ Descartado")
                del mensajes_pendientes[ultimo_msg_id]
                ultimo_msg_id = None

    await client.start()
    print("🚀 Bot activo con multimedia!")
    await client.run_until_disconnected()

asyncio.run(main())