import urllib.request, urllib.parse, json, os

API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY", "")
print(f"API Key prezenta: {'DA' if API_KEY else 'NU'}")
print(f"API Key primele 10 char: {API_KEY[:10] if API_KEY else 'LIPSA'}")

# Test simplu
q = urllib.parse.urlencode({
    "query": "EB Dent Cluj-Napoca stomatolog",
    "key": API_KEY,
    "language": "ro"
})
url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?{q}"
print(f"URL test: {url[:80]}...")

try:
    with urllib.request.urlopen(url, timeout=15) as r:
        data = json.loads(r.read())
    print(f"Status API: {data.get('status')}")
    results = data.get('results', [])
    print(f"Rezultate gasite: {len(results)}")
    if results:
        print(f"Primul rezultat: {results[0].get('name')}")
        print(f"Place ID: {results[0].get('place_id')}")
        # Get details
        pid = results[0]['place_id']
        fields = "name,formatted_phone_number,opening_hours,rating"
        q2 = urllib.parse.urlencode({"place_id": pid, "fields": fields, "key": API_KEY, "language": "ro"})
        url2 = f"https://maps.googleapis.com/maps/api/place/details/json?{q2}"
        with urllib.request.urlopen(url2, timeout=15) as r2:
            det = json.loads(r2.read()).get("result", {})
        print(f"Telefon: {det.get('formatted_phone_number', 'N/A')}")
        oh = det.get('opening_hours', {})
        print(f"Weekday text: {oh.get('weekday_text', [])}")
    else:
        print(f"Error message: {data.get('error_message', 'N/A')}")
except Exception as e:
    print(f"EROARE: {e}")
