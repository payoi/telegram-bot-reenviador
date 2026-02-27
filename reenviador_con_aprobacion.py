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
        return ""
    
    # Eliminar menciones (@usuario, @canal)
    texto = re.sub(r'@\w+', '', texto)
    
    # Eliminar TODOS los enlaces (http, https, www, t.me, etc.)
    texto = re.sub(r'https?://\S+', '', texto)  # http:// y https://
    texto = re.sub(r'www\.\S+', '', texto)      # www.ejemplo.com
    texto = re.sub(r't\.me/\S+', '', texto)     # t.me/canal
    
    # Eliminar espacios múltiples
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    texto = re.sub(r'  +', ' ', texto)
    
    return texto.strip()

async def main():
    global ultimo_msg_id
    client = TelegramClient('reenviador', api_id, api_hash)

    @client.on(events.NewMessage(chats=canales_origen))
    async def nuevo_mensaje(event):
        global ultimo_msg_id
        
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
        
        # Guardar mensaje pendiente
        mensajes_pendientes[msg_id] = {
            'chat_id': chat_id,
            'mensaje': event.message,
            'editando': False,
            'texto_editado': None
        }
        ultimo_msg_id = msg_id
        
        # Enviar preview a mensajes guardados (sin reenviar)
        texto_limpio = await limpiar_texto(event.message.message)
        
        if event.message.media:
            await client.send_file('me', event.message.media, caption=texto_limpio if texto_limpio else "📷 Multimedia")
        elif texto_limpio:
            await client.send_message('me', texto_limpio, link_preview=False)

    @client.on(events.NewMessage(chats='me', outgoing=True))
    async def respuesta_usuario(event):
        global ultimo_msg_id
        texto = event.message.message.strip().lower()
        
        # Publicar
        if texto in ['si', 's', 'ok', '1']:
            if not ultimo_msg_id or ultimo_msg_id not in mensajes_pendientes:
                return
            
            msg_data = mensajes_pendientes[ultimo_msg_id]
            mensaje_orig = msg_data['mensaje']
            
            # Usar texto editado si existe
            if msg_data['texto_editado']:
                texto_final = msg_data['texto_editado'] + MI_FIRMA
            else:
                texto_limpio = await limpiar_texto(mensaje_orig.message)
                texto_final = (texto_limpio + MI_FIRMA) if texto_limpio else ""
            
            if mensaje_orig.media:
                await client.send_file(tu_canal, mensaje_orig.media, caption=texto_final if texto_final else None)
            elif texto_final:
                await client.send_message(tu_canal, texto_final)
            
            await event.reply("✅ Publicado!")
            del mensajes_pendientes[ultimo_msg_id]
            ultimo_msg_id = None
        
        # Rechazar
        elif texto in ['no', 'n', '0']:
            if ultimo_msg_id and ultimo_msg_id in mensajes_pendientes:
                await event.reply("❌ Descartado")
                del mensajes_pendientes[ultimo_msg_id]
                ultimo_msg_id = None
        
        # Activar modo edición
        elif texto in ['editar', 'e', '2']:
            if ultimo_msg_id and ultimo_msg_id in mensajes_pendientes:
                mensajes_pendientes[ultimo_msg_id]['editando'] = True
                await event.reply("✏️ Escribe el nuevo texto:")
        
        # Guardar texto editado
        elif ultimo_msg_id and ultimo_msg_id in mensajes_pendientes:
            if mensajes_pendientes[ultimo_msg_id]['editando']:
                mensajes_pendientes[ultimo_msg_id]['texto_editado'] = event.message.message
                mensajes_pendientes[ultimo_msg_id]['editando'] = False
                await event.reply(f"✏️ Texto guardado. Responde 'si' para publicar o 'no' para cancelar")

    await client.start()
    print("🚀 Bot activo!")
    await client.run_until_disconnected()

asyncio.run(main())