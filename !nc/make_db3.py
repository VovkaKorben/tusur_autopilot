import sqlite3
import codecs
import pygame,pygame.freetype,pygame.gfxdraw
import os, sys, traceback, random
from pygame.locals import K_ESCAPE
import math

# 5/5
HOUSE_DENSITY = 5
TRESHOLD = 5

#make_data = True
make_data = False


W = 1300
H = 980
MARGIN = 10

FPS = 10
running = True
clock = pygame.time.Clock()

CLR_BG = (0x14,0x1E,0x27)
CLR_LINE = (0x004ee1)
CLR_ADDED = (0xffff00)
CLR_POINTS = (0xff483d)
CLR_PTS = (0x3bd200)
CLR_PTE = (0xd20000)
CLR_PATH = (0x3bd233)

def line_len(x1,y1,x2,y2):
        return math.sqrt( pow(x1-x2,2) + pow(y1-y2,2))


try:
    con = sqlite3.connect('map.db')
    cur = con.cursor()

    # read data from text file
    if make_data:
        init = ["drop table if exists `names`;",
        "CREATE TABLE `names` (`id` INTEGER PRIMARY KEY,`name` TEXT);",
        "drop table if exists `coords`;",
        "CREATE TABLE `coords` (`id` INTEGER,`order` INTEGER,`x` REAL,`y` REAL);",
        ]
        insert = [
        "insert into `names` (`id`,`name`) VALUES({},'{}');",
        "insert into `coords` (`id`,`order`,`x`,`y`) VALUES({},{},{},{});",
        ]
        closeup = ["CREATE INDEX `street_id` ON `coords` (id ASC);"]
        for sql in init:
            cur.execute(sql)
        con.commit()

        count = 0
        with codecs.open('corel.txt', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # print ("#{} {}".format(count,line))
                a = line.split("\t")
                
                # street name
                sql = insert[0].format(count,a[0])
                cur.execute(sql)
                con.commit()

                #coords
                pt=0
                for cc in range(1,len(a)):
                    coords = a[cc].split(",")
                    sql = insert[1].format(count,pt,coords[0],coords[1])
                    cur.execute(sql)
                    
                    pt+=1
                count+=1
        con.commit()
        f.close()   
        
        # создаем ключи
        for sql in closeup:
            cur.execute(sql)
        con.commit() 
        del pt,a,cc,sql,count,line,coords,init,closeup,insert,f
        print('-------------------------------------------------')        
        print('База загружена из текстового файла')
        

    del make_data

    nodes_count = -1
    nodes = [] 
    graph = [] 

  
    cur.execute("select count(distinct id) from coords;")
    rows = cur.fetchall()
    cnt = rows[0][0]
    print('-------------------------------------------------')        
    print('Найдено в базе улиц: {}'.format(cnt))
    for street_idx in range(cnt):
        cur.execute("select x,y from coords where id={};".format(street_idx))
        segments = cur.fetchall()   
        nodes_count+=1

        # сохраняем первую точку первого сегмента
        nodes.append({"street":street_idx,"segment":0,"pos":[segments[0][0],segments[0][1]]})
        
        for segment_idx in range(1,len(segments)):
            
            
            # находим длину сегмента
            l=line_len(segments[segment_idx-1][0],segments[segment_idx-1][1],segments[segment_idx][0],segments[segment_idx][1])
            
            # вычисляем, сколько у нас влезает "домов" на этот сегмент
            house_per_segment = (int)(l // HOUSE_DENSITY)
            
            for sub in range(1,house_per_segment+1):
                # находим координты этого дома
                nx = segments[segment_idx-1][0] + (segments[segment_idx][0] - segments[segment_idx-1][0]) / house_per_segment * sub
                ny = segments[segment_idx-1][1] + (segments[segment_idx][1] - segments[segment_idx-1][1]) / house_per_segment * sub
                
                # заносим его в ноды
                nodes.append({"street":street_idx,"segment":segment_idx-1,"pos":[nx,ny]})
                nodes_count+=1

                # добавляем граф, с длиной
                sub_len = line_len( nodes[nodes_count-1]["x"],nodes[nodes_count-1]["y"], nx,ny)
                graph.append({"start":nodes_count-1,"end":nodes_count,"len":sub_len,"type":0})
           

    del cnt,l,nx,ny,rows,street_idx,segment_idx,house_per_segment,sub,sub_len,segments,nodes_count
  
    graph_count = len(graph)
    print('Создано нодов: {}'.format(len(nodes)))
    print('Создано графов: {}'.format(graph_count))

    def graph_exists(graph,i,j):
        for g in graph:
            if (((g["start"]==i) and (g["end"]==j)) or ((g["start"]==j) and (g["end"]==i))):
                return True
        return False
    
    
    """
    проверяем каждую точку улицы на близость со всеми точками со всех других улиц
    если расстояние позволяет - делаем граф между ними
    """
    
    """
    for ns in range(len(nodes)):
        for nd in range(len(nodes)):
            # если разные улицы
            if (nodes[ns]["street"] != nodes[nd]["street"]):
                l = line_len(nodes[ns]["x"],nodes[ns]["y"],nodes[nd]["x"],nodes[nd]["y"]) 
                if ((l<=TRESHOLD) and (not graph_exists(graph,ns,nd))):
                    print("Connect {}-{}".format(ns,nd))   
                    graph.append({"start":ns,"end":nd,"len":l,"type":1})   

    print('Добавлено графов: {}'.format(len(graph)-graph_count))
    """


    

    # calculate map map borders
    minx = maxx = nodes[0]["x"]
    miny = maxy = nodes[0]["y"]
    for i in range(1,len(nodes)):
        if (nodes[i]["x"]>maxx): maxx = nodes[i]["x"]
        if (nodes[i]["x"]<minx): minx = nodes[i]["x"]
        if (nodes[i]["y"]>maxy): maxy = nodes[i]["y"]
        if (nodes[i]["y"]<miny): miny = nodes[i]["y"]
    
    # calculate map dimensions
    kx = (W-MARGIN*2) / (maxx - minx)
    ky = (H-MARGIN*2) / (maxy - miny)
    k=kx if kx<ky else ky
    del kx,ky,i

    def geo2screen(pt): 
        global k,minx,miny,H
        x = pt[0]-minx
        y = pt[1]-miny
        x *= k
        y *= k
        x += MARGIN
        y += MARGIN
        y = H - y # flip vertical
        return [x,y]
    
    def screen2geo(pt): 
        global k,minx,miny,H
        y = H - pt[1]
        x = pt[0] - MARGIN 
        y = y - MARGIN 
        x /= k
        y /= k
        x += minx
        y += miny
        return [x,y]


   

    def get_nearest_node(x,y):
        global nodes
        idx = -1
        min_len = line_len( nodes[0]["x"], nodes[0]["y"],x,y)
        for n in range(1,len(nodes)):
                l = line_len( nodes[n]["x"], nodes[n]["y"],x,y)
                if (l<min_len):
                    idx = n
                    min_len = l
        return idx
                

    def calc_path(path):
        global nodes
        path["start_geo"] = screen2geo(path["start_screen"])
        path["end_geo"] = screen2geo(path["end_screen"])
        path["start_node"] = get_nearest_node(path["start_geo"][0],path["start_geo"][1])
        path["end_node"] = get_nearest_node(path["end_geo"][0],path["end_geo"][1])

    path = {
    "start_screen": [100,100],
    "end_screen": [500,500]
    }
    
    calc_path(path)

    try:
        pygame.init()
        pygame.display.set_caption("Васька")
        surf_act = pygame.display.set_mode((W, H))
        #fnt = pygame.freetype.Font(os.path.join(scriptpath, 'app.ttf'), 10)

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: sys.exit()
                elif event.type == pygame.KEYDOWN: 
                    if (event.key == K_ESCAPE):
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN: 
                    if (event.button == 1): 
                        path["start_screen"] = event.pos
                        calc_path(path)
                    elif (event.button == 3): 
                        path["end_screen"] = event.pos
                        calc_path(path)




            # BG
            surf_act.fill(CLR_BG) 
            # рисуем графы
            for g in graph:
                pt0 = [ nodes[g["start"]]["x"], nodes[g["start"]]["y"] ]
                pt1 = [ nodes[g["end"]]["x"], nodes[g["end"]]["y"] ] 
                pt0 = geo2screen( pt0 )
                pt1 = geo2screen( pt1 )
                # разные цвета для стандартных/добавленных графов
                if (g["type"]==0): pygame.draw.line(surf_act,CLR_LINE , pt0, pt1, 1)
                else :             pygame.draw.line(surf_act,CLR_ADDED, pt0, pt1, 1)
            # рисуем домики
            for n in nodes:
                pt = [ n["x"], n["y"] ]
                pt = geo2screen( pt )
                pygame.draw.circle(surf_act, CLR_POINTS, pt, 1, 0)
            
            # start/end points                
            pygame.draw.circle(surf_act, CLR_PTS, (path["start_screen"][0],path["start_screen"][1]), 6, 0)
            pygame.draw.circle(surf_act, CLR_PTE, (path["end_screen"][0],path["end_screen"][1]), 6, 0)
            
            pygame.draw.line(surf_act,CLR_PATH, 
            (path["start_screen"][0],path["start_screen"][1]), 
            nodes[path["start_node"]["x"]]  pt1,
             1)

            pygame.display.flip()
            clock.tick(FPS)

    finally:
        pygame.quit()
                

except Exception as e:
    print()
    print("\n=-=-=- ERROR =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=\n")
    e = sys.exc_info()[1]
    print(e.args[0])
    traceback.print_exc()
    print("\n=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-\n")



