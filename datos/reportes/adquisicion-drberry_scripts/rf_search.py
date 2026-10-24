import os, sys, json, requests
KEY=os.environ["ROBOFLOW_API_KEY"].strip()
ws, proj, out = sys.argv[1:4]
allr=[]; off=0
while True:
    r=requests.post("https://api.roboflow.com/%s/%s/search"%(ws,proj), params={"api_key":KEY},
                    json={"offset":off,"limit":250,"fields":["id","name","split","created","labels"]}, timeout=120)
    if r.status_code!=200:
        print("status",r.status_code, r.text[:300].replace(KEY,"<REDACTED>")); break
    d=r.json(); res=d.get("results",[])
    allr+=res; off+=len(res)
    if not res or len(res)<250 or off>=d.get("total",0): break
json.dump(allr, open(out,"w"), indent=1)
print(proj, "n", len(allr), "total", d.get("total"))
