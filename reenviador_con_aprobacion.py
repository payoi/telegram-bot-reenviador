import asyncio
import os
import re
from telethon import TelegramClient, events, Button

# ⚙️ Variables de entorno
api_id = int(os.getenv('API_ID'))
api_hash = os.getenv('API_HASH')
tu_canal = int(os.getenv('TU_CANAL'))
canales_origen = [int(x.strip()) for x in os.getenv('CANALES_ORIGEN').split(',')]

# 🎨 Tu firma personalizada (cámbiala como quieras)
MI_FIRMA = "\n\n🔔 Únete: @NotiGlobalVE"  # Cambia esto por tu marca

# Diccionario para guardar mensajes pendientes
mensajes_pendientes = {}

async def limpiar_texto(texto):
    """Elimina menciones y links del canal original"""
    if not texto:
        return texto
    
    # Eliminar menciones de canales (@nombrecanal)
    texto = re.sub(r'@\w+', '', texto)
    
    # Eliminar URLs de Telegram
    texto = re.sub(r'https?://t\.me/\S+', '', texto)
    
    # Limpiar espacios múltiples
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    texto = texto.strip()
    
    return texto

async def main():
    client = TelegramClient('reenviador', api_id, api_hash)
    
    @client.on(events.NewMessage(chats=canales_origen))
    async def nuevo_mensaje(event):
        if not event.message.message and not event.message.media:
            return

        msg_id = event.message.id
        chat_id = event.chat_id
        
        # Guardar mensaje original
        mensajes_pendientes[msg_id] = {
            'chat_id': chat_id,
            'mensaje': event.message
        }
        
        # Preparar vista previa
        texto_limpio = await limpiar_texto(event.message.message)

if texto_limpio:
    preview = texto_limpio  # Sin "MENSAJE NUEVO"
else:
    preview = "📷 Multimedia"

botones = [
    [
        Button.inline("✅ PUBLICAR", f"pub_{msg_id}"),
        Button.inline("✏️ EDITAR", f"edit_{msg_id}")
    ],
    [
        Button.inline("❌ DESCARTAR", f"del_{msg_id}")
    ]
]

await client.send_message(
    'me',
    preview,  # Sin la marca "De: Canal"
    buttons=botones,
    link_preview=False
)

    @client.on(events.CallbackQuery)
    async def callback(event):
        data = event.data.decode()
        partes = data.split('_')
        accion = partes[0]
        msg_id = int(partes[1])
        
        if msg_id not in mensajes_pendientes:
            await event.answer("⚠️ Mensaje expirado", alert=True)
            return
        
        mensaje_orig = mensajes_pendientes[msg_id]['mensaje']
        chat_id = mensajes_pendientes[msg_id]['chat_id']
        
        if accion == "pub":
            # Publicar con firma
            texto_limpio = await limpiar_texto(mensaje_orig.message)
            
            if texto_limpio:
                texto_final = texto_limpio + MI_FIRMA
            else:
                texto_final = MI_FIRMA
            
            # Reenviar el mensaje
            if mensaje_orig.media:
                await client.send_file(
                    tu_canal,
                    mensaje_orig.media,
                    caption=texto_final if texto_final != MI_FIRMA else None
                )
            else:
                await client.send_message(tu_canal, texto_final)
            
            await event.edit("✅ ¡Publicado en tu canal!")
            del mensajes_pendientes[msg_id]
        
        elif accion == "edit":
            await event.edit(
                "✏️ **MODO EDICIÓN**\n\n"
                "Responde a ESTE mensaje con el texto que quieres publicar.\n\n"
                f"Texto original:\n{await limpiar_texto(mensaje_orig.message) or '(Sin texto)'}\n\n"
                "Comandos:\n"
                "/publicar - Publicar tu versión editada\n"
                "/cancelar - Volver al menú"
            )
            
            # Marcar como en edición
            mensajes_pendientes[msg_id]['editando'] = True
        
        elif accion == "del":
            await event.edit("❌ Descartado")
            del mensajes_pendientes[msg_id]

    @client.on(events.NewMessage(chats='me', incoming=True))
    async def mensaje_editado(event):
        """Captura tu respuesta para editar el mensaje"""
        if event.message.message.startswith('/'):
            return
        
        # Buscar si hay algún mensaje en modo edición
        for msg_id, data in mensajes_pendientes.items():
            if data.get('editando'):
                # Guardar texto editado
                mensajes_pendientes[msg_id]['texto_editado'] = event.message.message
                mensajes_pendientes[msg_id]['editando'] = False
                
                botones = [
                    [Button.inline("✅ PUBLICAR EDITADO", f"pubedit_{msg_id}")],
                    [Button.inline("❌ CANCELAR", f"del_{msg_id}")]
                ]
                
                await event.reply(
                    f"✏️ **Mensaje editado:**\n\n{event.message.message}\n\n¿Publicar?",
                    buttons=botones
                )
                break

    @client.on(events.CallbackQuery(pattern=b'pubedit_'))
    async def publicar_editado(event):
        msg_id = int(event.data.decode().split('_')[1])
        
        if msg_id not in mensajes_pendientes:
            await event.answer("⚠️ Mensaje expirado", alert=True)
            return
        
        texto_editado = mensajes_pendientes[msg_id].get('texto_editado', '')
        texto_final = texto_editado + MI_FIRMA
        
        mensaje_orig = mensajes_pendientes[msg_id]['mensaje']
        
        # Publicar
        if mensaje_orig.media:
            await client.send_file(tu_canal, mensaje_orig.media, caption=texto_final)
        else:
            await client.send_message(tu_canal, texto_final)
        
        await event.edit("✅ ¡Versión editada publicada!")
        del mensajes_pendientes[msg_id]

    await client.start()
    print("🚀 Bot de reenvío con aprobación activado!")
    print("✏️ Modo edición habilitado")
    print("📱 Revisa tus 'Mensajes Guardados' en Telegram")
    await client.run_until_disconnected()

asyncio.run(main())