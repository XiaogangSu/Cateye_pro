from osgeo import gdal
from osgeo import ogr
from osgeo import osr
import os
import sys
import math
import pandas as pd
import numpy as np
import copy
from tkinter import filedialog as fd
from tkinter import *
import pdb

class line_raster_pro():
    def __init__(self):
        print('开始处理！')
        gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "NO")
        gdal.SetConfigOption("SHAPE_ENCODING", "")
        ogr.RegisterAll()
        self.driver = ogr.GetDriverByName('ESRI Shapefile')
        
        path_name = fd.askopenfilename(initialdir = "D:/Data/",title = "选择shp文件",filetypes = (("shp files","*.shp"),(" all files","*.*")))
        raster_pathname = fd.askopenfilename(initialdir = "D:/Data/",title = "选择shp文件",filetypes = (("tif files","*.tif"),(" all files","*.*")))
        (self.path, self.name) = os.path.split(path_name)
        (self.rasterpath, self.rastername) = os.path.split(raster_pathname)
        self.save_name = self.name[:-4]+'_'+self.rastername[:-4]+'_'
        if os.path.exists(os.path.join(self.path,'output')):
            pass
        else:
            os.mkdir(os.path.join(self.path,'output'))

        length = input('输入抽稀间隔(米)： ')
        self.length = float(length)
    
    #同cor_tr，返回输入列表的所有列
    def cor_tr2(self, data, epsg1, epsg2, lon_index, lat_index, alt_index):
        gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "NO")
        gdal.SetConfigOption("SHAPE_ENCODING", "")
        ogr.RegisterAll()
        driver = ogr.GetDriverByName('ESRI Shapefile')
        sr = osr.SpatialReference()
        print('espg1:',epsg1,'  esgp2:',epsg2)
        sr.ImportFromEPSG(epsg1)
        sr_tar = osr.SpatialReference()
        sr_tar.ImportFromEPSG(epsg2)
        datacopy = copy.deepcopy(data)
        data_tr = datacopy
        i = -1
        for val in datacopy:
            i=i+1
            temppoint = ogr.Geometry(ogr.wkbPoint)
            temppoint.AssignSpatialReference(sr)
            temppoint.AddPoint(val[lon_index], val[lat_index], val[alt_index])
            # print('temppoint:',temppoint)
            temppoint.TransformTo(sr_tar)
            # print(temppoint.GetX(),temppoint.GetY(),temppoint.GetZ())
            data_tr[i][lon_index] = temppoint.GetX()
            data_tr[i][lat_index] = temppoint.GetY()
            data_tr[i][alt_index] = temppoint.GetZ()
            # print(data_tr[i])
            # pdb.set_trace()
            # data_tr.append([temppoint.GetX(),temppoint.GetY(), temppoint.GetZ()])
        return(data_tr)

    def savecsv(self, savedata_list, savename, savepath):  #保存list到csv 参数：保存数据（list），保存文件名（str）,保存路径（str）
        path = savepath
        name = savename
        savedata_df = pd.DataFrame(savedata_list)
        savedata_df.to_csv(os.path.join(path, name), index=False, header=False, encoding='utf-8-sig')
        print(savename + '保存成功！')

    def ReadLineshp(self):
        data_path = self.path
        data_name = self.name
        ds = ogr.Open(os.path.join(data_path, data_name), 0)
        # ds = ogr.Open(data_name, 0)
        if ds == None:
            print('打开文件%s失败！' % os.path.join(data_path, data_name))
        else:
            print('打开文件%s成功！' % os.path.join(data_path, data_name))
        lyr = ds.GetLayer(0)
        spatialref = lyr.GetSpatialRef()
        self.epsg = int(spatialref.GetAttrValue('AUTHORITY', 1))
        feanum = lyr.GetFeatureCount()
        if feanum != 1:
            print('数据个数不为1，请检查数据"%s"' %data_name)
            sys.exit()
        feature = lyr.GetNextFeature()
        ft_geo = feature.geometry()
        points = ft_geo.GetPoints()   #获取点坐标
        # print(ft_geo)
        # print(points)
        if ft_geo.GetGeometryName() != 'LINESTRING':    #返回要素类型
            print('要素类型错误，请检查数据！')
            sys.exit()
        point_num = len(points)
        print('点个数为%d'%point_num)
        output_points = []   #存储分割后的点坐标（投影后）
        contour_length = self.length   #间隔距离
        for i in range(point_num-1):
            start_x = points[i][0]
            start_y = points[i][1]
            end_x = points[i+1][0]
            end_y = points[i+1][1]
            # print(start_x,start_y,end_x,end_y)
            dis = math.sqrt(pow((end_y-start_y),2)+pow((end_x-start_x),2))
            # print('dis=%f' % dis)
            if dis<=contour_length:
                output_points.append((start_x, start_y))
                # output_points.append((end_x, end_y))
                continue

            if start_x!=end_x:
                k = (end_y-start_y)/(end_x-start_x)
                n = (end_x - start_x)/abs(end_x - start_x) #判断减价,+1表示开始点在前，结束点在后
                # print('n=',n)
                m = contour_length/math.sqrt(1+pow(k,2))
                dx = m*n
                dy = m*k*n
                # print('斜率=%f,dx=%f,dy=%f'%(k,dx,dy))
                while dis > contour_length:
                    # print('dis=%f,x=%f,y=%f'%(dis,start_x,start_y))
                    output_points.append((start_x, start_y))
                    start_x = start_x + dx
                    start_y = start_y + dy
                    dis = math.sqrt(pow((end_y-start_y),2)+pow((end_x-start_x),2))
                output_points.append((end_x,end_y))
            elif start_x==start_y:
                n = (end_y - start_y) / abs(end_y - start_y)  # 判断减价,+1表示开始点在前，结束点在后
                # print('n=', n)
                dx = 0
                dy = contour_length*n
                while dis > contour_length:
                    # print('dis=%f,x=%f,y=%f'%(dis,start_x,start_y))
                    output_points.append((start_x, start_y))
                    start_x = start_x + dx
                    start_y = start_y + dy
                    dis = math.sqrt(pow((end_y-start_y),2)+pow((end_x-start_x),2))

            # print('lastpoint:', output_points[len(output_points) - 1])
        output_points.append((points[len(points)-1][0],points[len(points)-1][1]))
        print('allpoints_num=',len(output_points))
        return(output_points)

    def ReadRaster(self):
        points = self.ReadLineshp()
        # for i in range(100):
        #     print(points[i])
        in_ds = gdal.Open(os.path.join(self.rasterpath, self.rastername))
        in_band = in_ds.GetRasterBand(1)
        in_transform = in_ds.GetGeoTransform()
        in_projection = in_ds.GetProjection()
        nodata = in_band.GetNoDataValue()
        print(in_transform)
        print(in_projection)
        print('nodata:', nodata)
        inv_transform = gdal.InvGeoTransform(in_transform)
        final_output = []
        for i in range(len(points)):
            offsets = gdal.ApplyGeoTransform(inv_transform, points[i][0], points[i][1])
            xoff, yoff = map(int, offsets)
            if xoff>=31250 or yoff>=51213:
                print('xoff=%d,yoff=%d,i=%d,超出栅格范围'%(xoff,yoff,i))
                sys.exit()
            value = in_band.ReadAsArray(xoff,yoff,1,1)[0,0]
            if value == nodata:
                continue
            else:
                final_output.append([points[i][0],points[i][1],float(value)])
                # print('point:',points[i][0],points[i][1],float(value))
        # for i in range(20):
        #     print(final_output[i],type(final_output[i]))
        print('self.epsg:', self.epsg)
        final_output_tr = self.cor_tr2(final_output,self.epsg,4326,1,0,2)
        # print(final_output[0])
        # print(final_output_tr[0])
        self.savecsv(final_output_tr, 'wgs84_'+self.save_name+'.csv', os.path.join(self.path,'output'))
        return(final_output_tr)

    def savejson(self):
        data = self.ReadRaster()
        f = open(os.path.join(self.path,'output',self.save_name+str(self.length)+'间隔.geojson'), 'w')
        f.write('[')
        # for val in data:
        #     strval = str(val)
        #     f.write(strval)
        #     f.write(',')
        
        for i in range(len(data)):
            strval = str(data[i])
            f.write(strval)
            if i == len(data)-1:
                pass
            else:
                f.write(',')
        f.write(']')
        f.close()


if __name__ =='__main__':
    ex = line_raster_pro()
    ex.savejson()
