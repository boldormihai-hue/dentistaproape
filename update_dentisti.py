import json, time, os, re, urllib.request, urllib.parse
from datetime import datetime

API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
DATA_FILE = "dentistaproape/data/dentisti.json"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def search_place(name, city):
    q = urllib.parse.urlencode({"query": f"{name} {city} Romania dentist", "key": API_KEY, "language": "ro"})
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?{q}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        results = data.get("results", [])
        return results[0]["place_id"] if results else None
    except Exception as e:
        log(f"  Eroare search: {e}")
        return None

def get_details(place_id):
    fields = "name,formatted_phone_number,international_phone_number,formatted_address,opening_hours,rating,user_ratings_total,photos,website,geometry,url"
    q = urllib.parse.urlencode({"place_id": place_id, "fields": fields, "key": API_KEY, "language": "ro"})
    url = f"https://maps.googleapis.com/maps/api/place/details/json?{q}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read()).get("result", {})
    except Exception as e:
        log(f"  Eroare details: {e}")
        return {}

def photo_url(ref):
    return f"https://maps.googleapis.com/maps/api/place/photo?photoreference={ref}&maxwidth=800&key={API_KEY}"

def parse_program(details):
    DAYS = ["Duminica","Luni","Marti","Miercuri","Joi","Vineri","Sambata"]
    RO = {"Duminica":"Duminica","Luni":"Luni","Marti":"Marti","Miercuri":"Miercuri","Joi":"Joi","Vineri":"Vineri","Sambata":"Sambata"}
    prog = {v: "Contactati clinica" for v in RO.values()}
    for p in details.get("opening_hours", {}).get("periods", []):
        o = p.get("open", {})
        c = p.get("close", {})
        idx = o.get("day", 0)
        key = DAYS[idx]
        ot = o.get("time", "0000")
        ct = c.get("time", "0000") if c else "0000"
        if ot == "0000" and ct == "0000":
            prog[key] = "Non-stop"
        else:
            prog[key] = f"{ot[:2]}:{ot[2:]}--{ct[:2]}:{ct[2:]}"
    return prog

def update(d):
    name = d["nume"]
    city = d["oras"]
    log(f"Procesez: {name} ({city})")
    pid = d.get("google_place_id") or search_place(name, city)
    if not pid:
        log("  Nu a fost gasit")
        return d, False
    time.sleep(0.3)
    det = get_details(pid)
    if not det:
        return d, False
    changed = False
    phone = det.get("international_phone_number") or det.get("formatted_phone_number", "")
    if phone and phone != d.get("telefon", ""):
        d["telefon"] = phone
        changed = True
        log(f"  Tel: {phone}")
    if det.get("website") and not d.get("website"):
        d["website"] = det["website"]
        changed = True
    addr = re.sub(r",?\s*Romania\s*$", "", det.get("formatted_address", ""), flags=re.I).strip()
    if addr and not d.get("adresa"):
        d["adresa"] = addr
        changed = True
    geo = det.get("geometry", {}).get("location", {})
    if geo:
        d["lat"] = geo.get("lat", 0)
        d["lng"] = geo.get("lng", 0)
        changed = True
    if det.get("url") and not d.get("google_maps_url"):
        d["google_maps_url"] = det["url"]
        changed = True
    if det.get("rating"):
        d["rating"] = round(det["rating"], 1)
        d["nr_recenzii"] = det.get("user_ratings_total", 0)
        changed = True
        log(f"  Rating: {d['rating']} ({d['nr_recenzii']} recenzii)")
    if det.get("opening_hours"):
        d["program"] = parse_program(det)
        changed = True
        log("  Program OK")
    photos = det.get("photos", [])
    if photos:
        d["poza"] = photo_url(photos[0]["photo_reference"])
        d["poze_google"] = [photo_url(p["photo_reference"]) for p in photos[:5] if p.get("photo_reference")]
        changed = True
        log(f"  {len(photos)} poze")
    d["google_place_id"] = pid
    d["ultima_actualizare"] = datetime.now().strftime("%Y-%m-%d")
    if changed:
        log("  Actualizat!")
    return d, changed

def main():
    if not API_KEY:
        print("GOOGLE_PLACES_API_KEY lipsa!")
        return
    if not os.path.exists(DATA_FILE):
        print(f"Fisier negasit: {DATA_FILE}")
        return
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    dentisti = data["dentisti"]
    log(f"Total: {len(dentisti)} cabinete")
    total = 0
    for i, d in enumerate(dentisti):
        log(f"[{i+1}/{len(dentisti)}]")
        dentisti[i], ch = update(d)
        if ch:
            total += 1
        if (i + 1) % 10 == 0:
            data["dentisti"] = dentisti
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            log(f"Salvat progres {i+1}/{len(dentisti)}")
        time.sleep(0.5)
    data["dentisti"] = dentisti
    data["ultima_actualizare"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"Gata! {total}/{len(dentisti)} actualizate")

if __name__ == "__main__":
    main()
