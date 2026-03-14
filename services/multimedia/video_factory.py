"""
NEXO SOBERANO - Video Factory v1.0
Motor multimedia optimizado para procesamiento 9:16 (Vertical) con bajo consumo de RAM.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("VideoFactory")

try:
    from moviepy import VideoFileClip, ColorClip, TextClip, CompositeVideoClip
except ImportError:
    logger.error("MoviePy no está instalado. Ejecuta: pip install moviepy")
    sys.exit(1)

def create_vertical_video(input_path: str, output_path: str, watermark_text: str = "NEXO SOBERANO") -> bool:
    """
    Corta un video a 9:16 (centrado) y lo guarda optimizando RAM.
    """
    clip = None
    final_video = None
    
    try:
        logger.info(f"Procesando video: {input_path}")
        clip = VideoFileClip(input_path)
        
        # 1. Definir dimensiones 9:16
        w, h = clip.size
        target_ratio = 9/16
        current_ratio = w/h
        
        if current_ratio > target_ratio:
            # Es más ancho (Landscape) -> Recortar laterales
            new_w = h * target_ratio
            x_center = w / 2
            # clip = clip.cropped(x1=x_center - new_w/2, y1=0, x2=x_center + new_w/2, y2=h)
            # En MoviePy 2.x, cropped es crop
            try:
                clip = clip.crop(x1=int(x_center - new_w/2), y1=0, x2=int(x_center + new_w/2), y2=h)
            except AttributeError:
                clip = clip.cropped(x1=int(x_center - new_w/2), y1=0, x2=int(x_center + new_w/2), y2=h)
        elif current_ratio < target_ratio:
            # Es más alto -> Recortar arriba/abajo
            new_h = w / target_ratio
            y_center = h / 2
            try:
                clip = clip.crop(x1=0, y1=int(y_center - new_h/2), x2=w, y2=int(y_center + new_h/2))
            except AttributeError:
                clip = clip.cropped(x1=0, y1=int(y_center - new_h/2), x2=w, y2=int(y_center + new_h/2))
            
        # 2. Redimensionar a standard HD Vertical (1080x1920)
        if clip.h != 1920:
            try:
                clip = clip.resized(height=1920)
            except AttributeError:
                clip = clip.resize(height=1920)
            
        # 3. Añadir Marca de Agua
        try:
            # Intentamos crear el clip de texto
            txt = TextClip(
                text=watermark_text, 
                font_size=70, 
                color="white",
                duration=clip.duration
            ).with_position(("center", 100))
            
            final_video = CompositeVideoClip([clip, txt])
        except Exception as e:
            logger.warning(f"No se pudo añadir texto (posible falta de ImageMagick): {e}")
            final_video = clip

        # 4. Exportar optimizado
        logger.info(f"Exportando a: {output_path}...")
        final_video.write_videofile(
            output_path, 
            codec="libx264", 
            audio_codec="aac",
            fps=30,
            preset="faster",
            threads=os.cpu_count() or 1,
            logger=None
        )
        
        logger.info("✅ Video generado exitosamente.")
        return True

    except Exception as e:
        logger.error(f"❌ Error en VideoFactory: {e}")
        return False
    
    finally:
        if clip: clip.close()
        if final_video and final_video is not clip: final_video.close()

def run_test():
    """Genera un clip de color de prueba."""
    logger.info("Iniciando prueba de VideoFactory (Modo Demo)...")
    
    output_dir = Path("cache/test_videos")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"test_9_16_{datetime.now().strftime('%H%M%S')}.mp4"
    
    try:
        # Usar ColorClip para evitar depender de archivos externos
        bg = ColorClip(size=(1080, 1920), color=(10, 20, 40), duration=3)
        
        logger.info("Generando video sintético (3s, Vertical)...")
        bg.write_videofile(
            str(out_file), 
            codec="libx264", 
            fps=24, 
            logger=None,
            preset="ultrafast"
        )
        
        bg.close()
        logger.info(f"✅ Test completado: {out_file}")
        logger.info(f"\n[OK] Video vertical generado en: {out_file.absolute()}")
        
    except Exception as e:
        logger.error(f"Fallo en el test: {e}")
        logger.info("\n[ERROR] El test falló.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NEXO Video Factory")
    parser.add_argument("--test", action="store_true", help="Ejecutar prueba de generación")
    parser.add_argument("--input", type=str, help="Ruta al video de entrada")
    parser.add_argument("--output", type=str, help="Ruta de salida")
    parser.add_argument("--text", type=str, default="NEXO SOBERANO", help="Texto de marca de agua")
    
    args = parser.parse_args()
    
    if args.test:
        run_test()
    elif args.input and args.output:
        create_vertical_video(args.input, args.output, args.text)
    else:
        parser.print_help()
