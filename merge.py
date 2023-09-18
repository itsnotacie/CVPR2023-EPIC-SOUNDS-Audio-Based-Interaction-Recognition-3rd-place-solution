import json


data1_path = "./test1.json"
with open(data1_path,'r') as f:
    data1 = json.loads(f.readlines()[0])  

data2_path = "./test2.json"
with open(data2_path,'r') as f:
    data2 = json.loads(f.readlines()[0])  

data3_path = "./test3.json"
with open(data3_path,'r') as f:
    data3 = json.loads(f.readlines()[0])  

data4_path = "./test4.json"
with open(data4_path,'r') as f:
    data4 = json.loads(f.readlines()[0])  

# print(x.keys())
# print(x['version'])
# print(x['challenge'])
# print(x['sls_pt'])
# print(x['sls_tl'])
# print(x['sls_td'])
# print(x['t_mod'])
# print(len(x['results']))

for k,v in data1['results'].items():
    #print(k,v)

    for i in range(44):
        v['interaction'][str(i)] = (v['interaction'][str(i)]*0.1+ \
                                data2['results'][k]['interaction'][str(i)]*0.4+ \
                                data3['results'][k]['interaction'][str(i)]*0.25+ \
                                data4['results'][k]['interaction'][str(i)]*0.25)/4
    
    #print(data1['results'][k])
    #break

with open("test.json",'w') as f:  
    json.dump(data1, f, ensure_ascii=False) 