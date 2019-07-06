import requests
import json
import geopy
import geopy.distance
from datetime import datetime, timezone

import secrets

office = (37.4074303728006, -122.070557984898)
#url = 'http://nyus.joshuawise.com/softee.json'
url = 'https://www.followmee.com/api/tracks.aspx?key=b8f203caee3bdfc3264240173caac188&username=mistersofteenorcal&output=json&function=currentforalldevices'
max_age = 300
max_dist = 3

geolocator = geopy.geocoders.Nominatim(user_agent = "softee-tracker/0.1")

class Truck:
    def __init__(self, name, seen, coordinates, speed):
        self.name = name
        self.seen = seen
        self.coordinates = coordinates
        self.speed = speed
    
    @property
    def distance(self):
        return geopy.distance.distance(office, self.coordinates)
    
    @property
    def age(self):
        now = datetime.now(timezone.utc)
        return (now - self.seen).seconds
    
    @property
    def mapsurl(self):
        return f"https://www.google.com/maps/place/{self.coordinates[0]},{self.coordinates[1]}"
    
    @property
    def location(self):
        return geolocator.reverse(f"{self.coordinates[0]}, {self.coordinates[1]}")

def get_trucks():
    r = requests.get(url)
    d = json.loads(r.text)
    now = datetime.now(timezone.utc)
    
    if "Error" in d:
        return {}
    
    trucks = {}
    
    for truck in d["Data"]:
        date = datetime.strptime(truck["Date"], "%Y-%m-%dT%H:%M:%S%z")
        age = (now - date).seconds
    
        if age > max_age:
            continue

        trucks[truck['DeviceName']] = Truck(seen = date, name = truck['DeviceName'], coordinates = (truck["Latitude"], truck["Longitude"]), speed = truck['Speed(mph)'])
    
    return trucks

def post_truck_seen(truck):
    payload = { "blocks": [
        {"type": "section", "text": { "type": "mrkdwn", "text": f"<!channel>\n\n:icecream: *Mister Softee is here!* :icecream:\n\nTruck \"{truck.name}\" was seen entering a {max_dist} mile radius of the office." } },
        {"type": "context", "elements": [{"type": "mrkdwn", "text": f"Truck is moving at {truck.speed} mph, {truck.distance.miles:.2f} mi from the office (<{truck.mapsurl}|{truck.location.address}>)." } ] }
    ] }
    r = requests.post(secrets.webhook_url, json = payload, headers = {'Content-type': 'application/json'})

def post_truck_gone(truck):
    payload = { "blocks": [
        {"type": "section", "text": { "type": "mrkdwn", "text": f"*Mister Softee has left the building.*  (Truck \"{truck.name}\" is speeding away at {truck.speed} mph, {truck.distance.miles:.2f} mi from the office.)" } },
    ] }
    r = requests.post(secrets.webhook_url, json = payload, headers = {'Content-type': 'application/json'})

trucks = get_trucks()
in_range = {}
with open('state.json') as fd:
    prev_in_range = json.load(fd)

for name in trucks:
    truck = trucks[name]
    print(f"Truck {truck.name} seen {truck.age} seconds ago")
    print(f"  {truck.distance.miles} miles away from office, {truck.speed} mph")
    
    if truck.distance.miles < max_dist:
        in_range[truck.name] = True
        if truck.name not in prev_in_range:
            print("  reporting arrival")
            post_truck_seen(truck)

with open('state.json', 'w') as fd:
    json.dump(in_range, fd)

for name in prev_in_range:
    if name not in in_range:
        print(f"reporting truck {name} departing")
        post_truck_gone(trucks[name])
