import json, time, os, re, urllib.request, urllib.parse
from datetime import datetime

API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
DATA_FILE = "dentistaproape/data/dentisti.json"
PHOTOS_DIR = "dentistaproape/data/photos"

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
        log(f"  Eroare search: {e}"); return None

def get_details(place_id):
    fields = "name,formatted_phone_number,international_phone_number,formatted_address,opening_hours,rating,user_ratings_total,photos,website,geometry,url"
    q = urllib.parse.urlencode({"place_id": place_id, "fields": fields, "key": API_KEY, "language": "ro"})
    url = f"https://maps.googleapis.com/maps/api/place/details/json?{q}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read()).get("result", {})
    except Exception as e:
        log(f"  Eroare details: {e}"); return {}

def download_photo(photo_ref, slug, index=0):
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    filename = f"{slug}_{index}.jpg"
    filepath = os.path.join(PHOTOS_DIR, filename)
    if os.path.exists(filepath):
        return f"data/photos/{filename}"
    url = f"https://maps.googleapis.com/maps/api/place/photo?photoreference={photo_ref}&maxwidth=800&key={API_KEY}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            with open(filepath, 'wb') as f:
                f.write(r.read())
        return f"data/photos/{filename}"
    except Exception as e:
        log(f"  Eroare poza: {e}"); return ""

def parse_program(details):
    """Extrage programul din Google Places - incearca periods, apoi weekday_text"""
    ZILE_EN = ["Duminica", "Luni", "Marti", "Miercuri", "Joi", "Vineri", "Sambata"]
    ZILE_RO = {
        "Duminica": "Duminică", "Luni": "Luni", "Marti": "Marți",
        "Miercuri": "Miercuri", "Joi": "Joi", "Vineri": "Vineri", "Sambata": "Sâmbătă"
    }
    prog = {v: "Închis" for v in ZILE_RO.values()}
    
    opening = details.get("opening_hours", {})
    periods = opening.get("periods", [])
    weekday_text = opening.get("weekday_text", [])
    
    if periods:
        for p in periods:
            o = p.get("open", {})
            c = p.get("close", {})
            idx = o.get("day", 0)
            if idx < 0 or idx > 6:
                continue
            key = ZILE_RO[ZILE_EN[idx]]
            ot = o.get("time", "0000")
            ct = c.get("time", "0000") if c else "0000"
            if ot == "0000" and (not c or ct == "0000"):
                prog[key] = "Non-stop"
            else:
                prog[key] = f"{ot[:2]}:{ot[2:]}–{ct[:2]}:{ct[2:]}"
        log(f"  Program din periods: {sum(1 for v in prog.values() if v not in ['Închis','Non-stop'])} zile")
        return prog
    
    if weekday_text:
        # weekday_text e in ordinea: Luni, Marti, ..., Duminica (pentru ro)
        # sau Monday, Tuesday, ..., Sunday (pentru en)
        zile_ordine = ["Luni", "Marți", "Miercuri", "Joi", "Vineri", "Sâmbătă", "Duminică"]
        for i, text in enumerate(weekday_text):
            if i >= len(zile_ordine):
                break
            zi = zile_ordine[i]
            # Extrage orele din text (ex: "Luni: 08:00–20:00" sau "Monday: 8:00 AM – 8:00 PM")
            parts = text.split(": ", 1)
            if len(parts) < 2:
                continue
            ore = parts[1].strip()
            if ore.lower() in ["closed", "închis", "inchis"]:
                prog[zi] = "Închis"
            elif "open 24 hours" in ore.lower() or "non-stop" in ore.lower():
                prog[zi] = "Non-stop"
            else:
                # Converteste AM/PM la 24h daca e cazul
                ore = convert_ampm(ore)
                prog[zi] = ore
        log(f"  Program din weekday_text: {weekday_text[0] if weekday_text else ''}")
        return prog
    
    return None

def convert_ampm(hours_str):
    """Converteste '9:00 AM – 6:00 PM' la '09:00–18:00'"""
    def to24(t):
        t = t.strip()
        if not t:
            return t
        try:
            if "AM" in t.upper() or "PM" in t.upper():
                from datetime import datetime as dt
                for fmt in ["%I:%M %p", "%I:%M%p", "%I %p"]:
                    try:
                        return dt.strptime(t.upper(), fmt.upper()).strftime("%H:%M")
                    except:
                        pass
        except:
            pass
        return t.replace(".", ":")
    
    for sep in ["–", "—", " - ", "-"]:
        if sep in hours_str:
            parts = hours_str.split(sep, 1)
            return f"{to24(parts[0].strip())}–{to24(parts[1].strip())}"
    return hours_str

def update(d):
    name = d["nume"]
    city = d["oras"]
    slug = d["slug"]
    log(f"Procesez: {name} ({city})")
    
    pid = d.get("google_place_id") or search_place(name, city)
    if not pid:
        log("  Nu a fost gasit"); return d, False
    time.sleep(0.3)
    
    det = get_details(pid)
    if not det:
        return d, False
    
    changed = False
    
    # Telefon
    phone = det.get("international_phone_number") or det.get("formatted_phone_number", "")
    if phone and phone != d.get("telefon", ""):
        d["telefon"] = phone
        changed = True
        log(f"  Tel: {phone}")
    
    # Website
    if det.get("website") and not d.get("website"):
        d["website"] = det["website"]
        changed = True
        log(f"  Site: {det['website'][:50]}")
    
    # Adresa
    addr = re.sub(r",?\s*Romania\s*$", "", det.get("formatted_address", ""), flags=re.I).strip()
    if addr:
        d["adresa"] = addr
        changed = True
    
    # GPS
    geo = det.get("geometry", {}).get("location", {})
    if geo:
        d["lat"] = geo.get("lat", 0)
        d["lng"] = geo.get("lng", 0)
        changed = True
    
    # Maps URL
    if det.get("url"):
        d["google_maps_url"] = det["url"]
        changed = True
    
    # Rating
    if det.get("rating"):
        d["rating"] = round(det["rating"], 1)
        d["nr_recenzii"] = det.get("user_ratings_total", 0)
        changed = True
        log(f"  Rating: {d['rating']} ({d['nr_recenzii']} recenzii)")
    
    # Program
    program = parse_program(det)
    if program:
        d["program"] = program
        changed = True
        log(f"  Program: {list(program.items())[:2]}")
    
    # Poze - descarca local
    photos = det.get("photos", [])
    if photos:
        if not d.get("poza") or "maps.googleapis.com" in d.get("poza", "") or not d.get("poza"):
            local_path = download_photo(photos[0]["photo_reference"], slug, 0)
            if local_path:
                d["poza"] = local_path
                changed = True
        extra = []
        for i, p in enumerate(photos[1:3], 1):
            if p.get("photo_reference"):
                lp = download_photo(p["photo_reference"], slug, i)
                if lp:
                    extra.append(lp)
        if extra:
            d["poze_extra"] = extra
        log(f"  {len(photos)} poze disponibile")
    
    d["google_place_id"] = pid
    d["ultima_actualizare"] = datetime.now().strftime("%Y-%m-%d")
    if changed:
        log("  Actualizat!")
    return d, changed

def main():
    if not API_KEY:
        print("GOOGLE_PLACES_API_KEY lipsa!"); return
    if not os.path.exists(DATA_FILE):
        print(f"Fisier negasit: {DATA_FILE}"); return
    
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    
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
