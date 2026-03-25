# 🎵 Directorio de Sonidos

Este directorio contiene los archivos de audio para la botonera de sonidos del bot.

## Archivos Requeridos

Coloca los siguientes archivos MP3 en este directorio:

| Archivo | Descripción | Duración Recomendada |
|---------|-------------|---------------------|
| `nexo.mp3` | Sonido de inicio/bienvenida | 1-3 segundos |
| `alert.mp3` | Sonido de alerta | 0.5-1 segundo |
| `success.mp3` | Sonido de éxito | 0.5-1 segundo |
| `error.mp3` | Sonido de error | 0.5-1 segundo |
| `laugh.mp3` | Sonido de risa | 1-2 segundos |
| `applause.mp3` | Sonido de aplausos | 2-3 segundos |
| `bell.mp3` | Sonido de campana | 0.5-1 segundo |
| `whistle.mp3` | Sonido de silbido | 1-2 segundos |

## Cómo Agregar Sonidos

### Opción 1: Descargar Sonidos Gratuitos

1. Ve a https://freesound.org
2. Busca el sonido que quieres
3. Descárgalo en formato MP3
4. Colócalo en este directorio con el nombre correcto

### Opción 2: Crear Sonidos Personalizados

Usa herramientas como:
- **Audacity**: https://www.audacityteam.org/ (Gratuito)
- **FL Studio**: https://www.image-line.com/ (Pago)
- **Ableton Live**: https://www.ableton.com/ (Pago)

### Opción 3: Usar Generadores de Sonido Online

- **Bfxr**: https://www.bfxr.net/ (Generador de sonidos retro)
- **Jsfxr**: https://sfxr.me/ (Generador de sonidos web)

## Especificaciones Técnicas

- **Formato**: MP3
- **Bitrate**: 128 kbps o superior
- **Frecuencia de muestreo**: 44.1 kHz
- **Duración máxima**: 30 segundos
- **Tamaño máximo**: 10 MB

## Ejemplo: Crear un Sonido con Audacity

1. Abre Audacity
2. Genera un tono: `Generate → Tones`
3. Ajusta la duración y frecuencia
4. Exporta como MP3: `File → Export → Export as MP3`
5. Guarda en este directorio

## Notas

- Si un archivo de sonido no existe, el bot lo ignorará sin error
- Los sonidos se reproducen secuencialmente
- La duración máxima es de 30 segundos por sonido
- Asegúrate de tener permisos para usar los sonidos

## Agregar Nuevos Sonidos al Bot

Para agregar nuevos sonidos, edita `bot.js` y agrega una entrada en el objeto `SOUNDS`:

```javascript
const SOUNDS = {
  'mi_sonido': { name: '🎵 Mi Sonido', file: 'sounds/mi_sonido.mp3', emoji: '🎵' },
  // ... otros sonidos
};
```

Luego reinicia el bot.
