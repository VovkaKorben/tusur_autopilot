import sqlite3
import codecs
import pygame,pygame.freetype,pygame.gfxdraw
import os, sys, traceback, random
from pygame.locals import K_ESCAPE
import math

HOUSE_DENSITY = 1
debug_print = True
make_data = False


W = 1800
H = 900
MARGIN = 20

FPS = 10
running = True
clock = pygame.time.Clock()

CLR_BG = (0x14,0x1E,0x27)
CLR_LINE = (0x004ee1)
CLR_SEL = (0xff,0x48,0x3d)


def line_len(x1,y1,x2,y2):
        return math.sqrt( pow(x1-x2,2) + pow(y1-y2,2))

def intersect_lines(x1,y1,x2,y2,x3,y3,x4,y4): 

    if ((y2 - y1) != 0): 
        q = (x2 - x1) / (y1 - y2)
        sn = (x3 - x4) + (y3 - y4) * q
        if (sn == 0):   return False 
        fn = (x3 - x1) + (y3 - y1) * q
        n = fn / sn
    else:
        if ((y3 - y4)==0):  return False
        n = (y3 - y1) / (y3 - y4)
    return [x3 + (x4 - x3) * n,  y3 + (y4 - y3) * n]


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

                if debug_print: print ("#{} {}".format(count,line))
                a = line.split("\t")
                
                # street name
                sql = insert[0].format(count,a[0])
                cur.execute(sql)
                con.commit()

                #coords
                pt=0
                for cc in range(1,len(a)):
                    coords = a[cc].split(",")
                    if debug_print: print ("--- {}".format(coords))
                    sql = insert[1].format(count,pt,coords[0],coords[1])
                    cur.execute(sql)
                    con.commit()
                    pt+=1
                count+=1
        f.close()   
        
        # создаем ключи
        for sql in closeup:
                cur.execute(sql)
                con.commit() 
        del pt,a,cc,sql,count,line,coords,init,closeup,insert,f

        

    del make_data

    nodes_count = -1
    nodes = [] # [line_id,x,y]
    graph = [] # [point1_id,point2_id,distance]

    segm_all = [] # собираем все сегменты в кучу, чтобы не перечитывать базу
    ends_all = [] # собираем все края в кучу, чтобы не перечитывать базу
    # добавляем номера домов, исходя из длины улицы
    

    cur.execute("select count(distinct id) from coords;")
    rows = cur.fetchall()
    cnt = rows[0][0]
    for street_idx in range(cnt):
        cur.execute("select x,y from coords where id={};".format(street_idx))
        segments = cur.fetchall()   
        nodes_count+=1

        # сохраняем первую точку первого сегмента
        nodes.append({"street":street_idx,"segment":0,"x":segments[0][0],"y":segments[0][1]})
        # сохраняем первую ноду  для последующей обработки
        ends_all.append(nodes_count)
        
        for segment_idx in range(1,len(segments)):
            
            # сохраняем сегмент для последующей обработки
            segm_all.append([street_idx,segments[segment_idx-1],segments[segment_idx]])
            
            # находим длину сегмента
            l=line_len(segments[segment_idx-1][0],segments[segment_idx-1][1],segments[segment_idx][0],segments[segment_idx][1])
            
            # вычисляем, сколько у нас влезает "домов" на этот сегмент
            house_per_segment = (int)(l // HOUSE_DENSITY)
            #print ("line: {}(sub:{}), len: {}".format(street_idx,house_per_segment,l)) 
            
            for sub in range(1,house_per_segment+1):
                # находим координты этого дома
                nx = segments[segment_idx-1][0] + (segments[segment_idx][0] - segments[segment_idx-1][0]) / house_per_segment * sub
                ny = segments[segment_idx-1][1] + (segments[segment_idx][1] - segments[segment_idx-1][1]) / house_per_segment * sub
                
                # заносим его в ноды
                nodes.append({"street":street_idx,"segment":segment_idx-1,"x":nx,"y":ny})
                nodes_count+=1

                # добавляем граф, с длиной
                sub_len = line_len( nodes[nodes_count-1]["x"],nodes[nodes_count-1]["y"], nx,ny)
                graph.append({"start":nodes_count-1,"end":nodes_count,"len":sub_len})
            
            # добавляем угловую ноду
            ends_all.append(nodes_count)

    del cnt,l,nx,ny,rows,street_idx,segment_idx,house_per_segment,sub,sub_len
  
    def graph_exists(graph,i,j):
        for g in graph:
            if (((g["start"]==i) and (g["end"]==j)) or ((g["start"]==j) and (g["end"]==i))):
                return True
        return False


"""
проверяем каждую точку улицы на близость со всеми точками со всех других улиц
если расстояние позволяет - делаем граф между ними
"""







    # проверяем концы сегментов на слияние
    TRESHOLD = 1.5
    for i in ends_all:
        checklist = ends_all.copy() 
        # remove itself
        checklist.remove(i)
        for j in checklist:
            l = line_len(nodes[i]["x"],nodes[i]["y"],nodes[j]["x"],nodes[j]["y"])
            if ((l<=TRESHOLD) and (not graph_exists(graph,i,j))):
                print("Connect {}-{}".format(i,j))   
                graph.append({"start":i,"end":j,"len":l})






    # проверяем сегменты на пересечение
    for i in range (len(segm_all)):
        for j in range(i+1,len(segm_all)):
            
            pt = intersect_lines(segm_all[i][1][0],segm_all[i][1][1],segm_all[i][2][0],segm_all[i][2][1],
                                 segm_all[j][1][0],segm_all[j][1][1],segm_all[j][2][0],segm_all[j][2][1])
            if (pt != False):
                print("Intersect: {}-{}".format(i,j))
                print(pt)
                pass


    

    # read map borders
    cur.execute("select min(x) as minx, min(y) as miny, max(x) as maxx, max(y) as maxy from coords;")
    rows = cur.fetchall()
    minx = rows[0][0]
    maxx = rows[0][2]
    miny = rows[0][1]
    maxy = rows[0][3]
    
    # calculate map dimensions
    dx = maxx - minx
    dy = maxy - miny
    kx = (W-MARGIN*2) / dx
    ky = (H-MARGIN*2) / dy
    k=kx if kx<ky else ky

    # read streets
    coords = []

    cur.execute("select `id`,`order`,`x`,`y` from coords order by `id` asc,`order` asc;")
    rows = cur.fetchall()
    pt = []
    prev_idx = -1
    for row in rows:
        if (prev_idx != row[0]):
            prev_idx = row[0]
            if prev_idx>0:
                coords.append(pt)
                pt = []    

        pt.append([row[2],row[3]])
    coords.append(pt)   
    del prev_idx,kx,ky,rows,pt,row;

    
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


    try:
        pygame.init()
        pygame.display.set_caption("Васька")
        surf_act = pygame.display.set_mode((W, H))
        #fnt = pygame.freetype.Font(os.path.join(scriptpath, 'app.ttf'), 10)

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: sys.exit()
                if event.type == pygame.KEYDOWN: 
                    if (event.key == K_ESCAPE):
                        running = False

            # BG
            surf_act.fill(CLR_BG) 
        
            for street in coords:
                for pt_index in range(1,len(street)): 
                    pt0 = geo2screen( street[pt_index-1] )
                    pt1 = geo2screen( street[pt_index] )
                    pygame.draw.line(surf_act,CLR_LINE, pt0, pt1, 2)

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



