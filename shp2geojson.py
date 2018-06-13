from __future__ import division
import os
import json
from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from math import sqrt, pow
import pyproj

class shp2geojson():
    # data_path = input('输入数据路径:')
    data_path = 'E:\cateye\data\Contour'
    # datapath = data_path.replace('\\', '/')
    # data_name = input('输入数据名称：')
    # ex_num = input('输入抽稀比例（1、10、11）：')
    data_name = 'gujiao_100.shp'
    layer_input = input('输入层级:')
    precision_select = {'8':[611.5, 3], '9':[305.7, 3], '10':[152.9, 4], '11':[76.4, 4], '12':[38.2, 4],
                        '13':[19.1, 5], '14':[9.6, 5], '15':[4.8, 5], '16':[2.4, 5], '17':[1.2, 6]}
    # threshold = float(threshold_input)
    qualify_list = list()
    disqualify_list = list()
    driver = ogr.GetDriverByName('ESRI Shapefile')
    sr = osr.SpatialReference()
    sr.ImportFromEPSG(4326)

    def __init__(self):
        gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "NO")
        gdal.SetConfigOption("SHAPE_ENCODING", "")
        ogr.RegisterAll()
        # self.threshold = THRESHOLD

    def point2LineDistance(self, point_a, point_b, point_c):
        """
        计算点a到点b c所在直线的距离
        :param point_a:
        :param point_b:
        :param point_c:
        :return:
        """
        # 首先计算b c 所在直线的斜率和截距
        if point_b[0] == point_c[0]:
            return (9999999)
        slope = (point_b[1] - point_c[1]) / (point_b[0] - point_c[0])
        intercept = point_b[1] - slope * point_b[0]
        # 计算点a到b c所在直线的距离
        distance = abs(slope * point_a[0] - point_a[1] + intercept) / sqrt(1 + pow(slope, 2))
        return (distance)

    def diluting(self, point_list):
        """
        抽稀
        :param point_list:二维点列表
        :return:
        """
        # print(point_list[::-1])
        qualify_list = list()
        if len(point_list) < 3:
            self.qualify_list.extend(point_list[::-1])
        else:
            # 找到与收尾两点连线距离最大的点
            max_distance_index, max_distance = 0, 0
            for index, point in enumerate(point_list):
                # print(index, point, len(point_list))
                if index in [0, len(point_list) - 1]:
                    # print(index, 'in', '[0, len(point_list) - 1]')
                    continue
                distance = self.point2LineDistance(point, point_list[0], point_list[-1])
                # print(distance)
                if distance > max_distance:
                    max_distance_index = index
                    max_distance = distance
            if max_distance < self.precision_select[self.layer_input][0]:
                self.qualify_list.append(point_list[-1])
                self.qualify_list.append(point_list[0])
            else:
                # 将曲线按最大距离的点分割成两段
                sequence_a = point_list[:max_distance_index]
                sequence_b = point_list[max_distance_index:]
                for sequence in [sequence_a, sequence_b]:
                    # print(sequence)
                    if len(sequence) < 3 and sequence == sequence_b:
                        self.qualify_list.extend(sequence[::-1])
                        # print(self.qualify_list)
                    else:
                        self.disqualify_list.append(sequence)
                        # print(self.disqualify_list)

    def daglus_compute(self, point_list):
        # print('抽稀前要素个数：', len(point_list))
        # print('抽稀前坐标：', point_list)
        self.diluting(point_list)
        while len(self.disqualify_list) > 0:
            self.diluting(self.disqualify_list.pop())
        # print('抽稀后要素个数：', len(self.qualify_list))
        # print('抽稀后坐标：', self.qualify_list)
        return(self.qualify_list)

    def read_data(self):
        print('开始读取数据。。。')
        data_path = self.data_path
        data_name = self.data_name
        ds = ogr.Open(os.path.join(data_path,data_name), 0)
        if ds == None:
            print('打开文件%s失败！' %os.path.join(data_path,data_name))
        else:
            print('打开文件%s成功！' %os.path.join(data_path,data_name))

        lyr = ds.GetLayer(0)
        feanum = lyr.GetFeatureCount()
        # print(lyr.GetSpatialRef())
        epsg_num = lyr.GetSpatialRef().GetAttrValue('AUTHORITY',1)
        epsg = 'epsg:'+ epsg_num
        print('feanum:', feanum)
        # 创建图层
        datasource_name = data_name[0:-4] + '_' + str(self.precision_select[self.layer_input][0]) +'_' + self.layer_input + '_daglus'
        if os.path.exists(datasource_name):
            self.driver.DeleteDataSource(datasource_name)
        shpsource = self.driver.CreateDataSource(datasource_name)  # 创建数据源，即文件夹，若该文件件已存在则会出错
        if shpsource is None:
            print('CreateDataSource失败！')
        layer_name = data_name[0:-4] + '_' + str(self.precision_select[self.layer_input][0]) +'_' + self.layer_input
        shpLayer = shpsource.CreateLayer(layer_name, self.sr, geom_type=ogr.wkbLineString)  # 在文件夹中创建图层,并制定坐标系
        # 添加字段
        contour = ogr.FieldDefn('contour', ogr.OFTReal)
        contour.SetWidth(4)
        shpLayer.CreateField(contour)
        # 创建feature
        defn = shpLayer.GetLayerDefn()
        feature = ogr.Feature(defn)

        final_dict = {}
        temp_geo_list = []
        utm_proj = pyproj.Proj(init = epsg)
        for i in range(feanum):
            if i/feanum in [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]:
                print(i/feanum)
            # print('i=', i)
            feat = lyr.GetNextFeature()
            geo = feat.geometry()
            gname = geo.GetGeometryName()
            point_tuple = geo.GetPoints()
            temp_list = []
            # print(type(point_tuple),point_tuple)
            # for i in range(0,len(point_tuple), int(self.ex_num)):
            #     val_list = list(point_tuple[i])
            #     temp_list.append(val_list)
            #将tuple转换为list
            for val in point_tuple:
                val_list = list(val)
                temp_list.append(val_list)
            # print(temp_list)
            duglas_list = self.daglus_compute(temp_list)
            cor_list = []
            for val_dug in duglas_list:
                x_tr, y_tr = utm_proj(val_dug[0], val_dug[1], inverse=True)
                cor_list.append([round(x_tr,self.precision_select[self.layer_input][1]), round(y_tr, self.precision_select[self.layer_input][1])])

            temp_dict = {}
            temp_dict_properties = {}
            temp_dict_properties['ID'] = feat.GetField('ID')
            temp_dict_properties['CONTOUR'] = feat.GetField('CONTOUR')
            temp_dict_geometry = {}
            temp_dict_geometry['type'] = gname
            temp_dict_geometry['coordinates'] = cor_list
            self.disqualify_list = []
            self.qualify_list = []

            temp_dict['geometry'] = temp_dict_geometry
            temp_dict['properties'] = temp_dict_properties
            temp_dict['type'] = 'Feature'
            temp_geo_list.append(temp_dict)

            # 在shp文件中添加数据
            # print('开始创建shp...')
            contour_line = ogr.Geometry(ogr.wkbLineString)
            for i in range(len(temp_dict_geometry['coordinates'])):
                temp_val = temp_dict_geometry['coordinates'][i]
                # print(temp_val, type(temp_val))
                contour_line.AddPoint(temp_val[0], temp_val[1])
            feature.SetField('contour', feat.GetField('CONTOUR'))
            feature.SetGeometry(contour_line)
            shpLayer.CreateFeature(feature)

        feature.Destroy()
        del ds
        final_dict['features'] = temp_geo_list
        final_dict['type'] = 'FeatureCollection'
        final_dict['name'] = data_name[:-4]
        save_dataname = data_name[0:-4] + '_' + str(self.precision_select[self.layer_input][0]) +'_' + \
                          self.layer_input + '.json'
        print('开始存储数据。。。')
        with open(os.path.join(data_path,save_dataname),'w') as f:
            json.dump(final_dict, f)



def main():
    ex = shp2geojson()
    ex.read_data()

main()