

from osgeo import gdal
import numpy as np
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsPointXY,
    QgsCoordinateReferenceSystem
)
import os

image_number = 2
output_file_path = os.path.join(os.path.dirname(QgsProject.instance().fileName()), f'georeferenced_{image_number}.tif')

print("Запуск скрипта геопривязки...")

source_raster = None
out_raster = None
vector_layer = None

try:
    
    if os.path.exists(output_file_path):
        try:
            os.remove(output_file_path)
            print("Существующий файл успешно удален.")
        except OSError as e:
            print(f"ОШИБКА: Не удалось удалить файл '{output_file_path}'. Он может быть занят другим процессом. Пожалуйста, закройте его в QGIS или в другой программе. {e}")
            raise # Передаем исключение дальше, чтобы скрипт завершился.

    
    raster_layer_name = '2'
    vector_layer_name = 'footprint'

    print(f"Поиск растрового слоя '{raster_layer_name}' в проекте...")
    raster_layer = QgsProject.instance().mapLayersByName(raster_layer_name)
    if not raster_layer:
        raise ValueError(f"Слой '{raster_layer_name}' не найден в проекте.")
    raster_layer = raster_layer[0]
    
    source_raster = gdal.Open(raster_layer.source())
    if source_raster is None:
        raise ValueError("Не удалось открыть исходный растр.")
    
    
    raster_x_size = source_raster.RasterXSize
    raster_y_size = source_raster.RasterYSize
    raster_bands_count = source_raster.RasterCount
    print(f"Растр успешно открыт. Размер: {raster_x_size}x{raster_y_size}, Каналов: {raster_bands_count}")
    
    
    band_arrays = []
    print("Чтение каналов в массивы...")
    for i in range(1, raster_bands_count + 1):
        band = source_raster.GetRasterBand(i)
        band_array = band.ReadAsArray().astype(np.float32)
        band_arrays.append(band_array)
        print(f"Канал {i} считан.")
    print("Все каналы считаны.")

    
    print("Создание копии растрового изображения...")
    driver = gdal.GetDriverByName('GTiff')
    out_raster = driver.Create(
        output_file_path,
        raster_x_size,
        raster_y_size,
        raster_bands_count,
        gdal.GDT_Float32
    )

    
    for i, arr in enumerate(band_arrays):
        out_band = out_raster.GetRasterBand(i + 1)
        out_band.WriteArray(arr)
        print(f"Массив канала {i + 1} записан в новый растр.")

    
    print(f"Поиск векторного слоя '{vector_layer_name}' в проекте...")
    vector_layers = QgsProject.instance().mapLayersByName(vector_layer_name)
    if not vector_layers:
        raise ValueError("Не удалось найти векторный слой. Проверьте его имя в панели Слои.")
    vector_layer = vector_layers[0]
    print("Векторный слой успешно найден.")
    
    
    print("Получение угловых координат из полигона...")
    footprint_points = []
    features = vector_layer.getFeatures()
    feature = next(features)
    
    geometry = feature.geometry()
    polygon = geometry.asPolygon()
    
    points = polygon[0]
    if len(points) == 5:
        nw_point = QgsPointXY(points[0])
        ne_point = QgsPointXY(points[1])
        se_point = QgsPointXY(points[2])
        sw_point = QgsPointXY(points[3])
        
        footprint_points.append((nw_point.x(), nw_point.y()))
        footprint_points.append((ne_point.x(), ne_point.y()))
        footprint_points.append((se_point.x(), se_point.y()))
        footprint_points.append((sw_point.x(), sw_point.y()))
        print("Угловые координаты получены.")

      
        vector_crs = vector_layer.crs()
        out_raster.SetProjection(vector_crs.toWkt())
        print("Проекция задана.")
        
        
        gcp_list = [
            gdal.GCP(footprint_points[0][0], footprint_points[0][1], 0, 0, 0),
            gdal.GCP(footprint_points[1][0], footprint_points[1][1], 0, raster_x_size - 1, 0),
            gdal.GCP(footprint_points[2][0], footprint_points[2][1], 0, raster_x_size - 1, raster_y_size - 1),
            gdal.GCP(footprint_points[3][0], footprint_points[3][1], 0, 0, raster_y_size - 1)
        ]
        
       
        out_raster.SetGCPs(gcp_list, out_raster.GetProjection())
        out_raster.FlushCache()
        
        print("Опорные точки установлены и растр сохранен.")
    else:
        raise ValueError("Полигон содержит не 4 точки. Проверьте ваш файл.")

except ValueError as ve:
    print(f"ОШИБКА: {ve}")
except Exception as e:
    print(f"ПРОИЗОШЛА НЕПРЕДВИДЕННАЯ ОШИБКА: {e}")

finally:
   
    source_raster = None
    out_raster = None
    print("Ресурсы освобождены. Скрипт завершен.")
