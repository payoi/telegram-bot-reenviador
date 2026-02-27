import asyncio
import os
from telethon import TelegramClient, events, Button

# ⚙️ Variables de entorno (Railway las leerá automáticamente)
api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
tu_canal = int(os.getenv('TU_CANAL'))

# Canales origen (separados por comas)
canales_origen = [int(x.strip()) for x in os.getenv('CANALES_ORIGEN').split(',')]

async def main():
    client = TelegramClient('reenviador', api_id, api_hash)
    
    @client.on(events.NewMessage(chats=canales_origen))
    async def nuevo_mensaje(event):
        if not event.message.message and not event.message.media:
            return

        botones = [
            [Button.inline("✅ PUBLICAR", f"ok_{event.message.id}_{event.chat_id}"),
             Button.inline("❌ DESCARTAR", f"no_{event.message.id}")]
        ]

        await client.send_message('me', event.message, buttons=botones)

    @client.on(events.CallbackQuery)
    async def callback(event):
        data = event.data.decode()
        partes = data.split('_')
        accion = partes[0]

        if accion == "ok":
            msg_id = int(partes[1])
            origen = int(partes[2])
            
            mensaje_original = await client.get_messages(origen, ids=msg_id)
            await client.send_message(tu_canal, mensaje_original)
            await event.edit("✅ Publicado en tu canal!")
        else:
            await event.edit("❌ Descartado")

    await client.start()
    print("🚀 Bot de reenvío con aprobación activado!")
    print("📱 Revisa tus 'Mensajes Guardados' en Telegram")
    await client.run_until_disconnected()

asyncio.run(main())