import React,{useMemo,useState}from'react';
import{MapContainer,TileLayer,CircleMarker,Popup,Tooltip,Marker,LayersControl,LayerGroup,useMap}from'react-leaflet';
import L from'leaflet';
import'leaflet/dist/leaflet.css';

const chokePoints=[
 {name:'Strait of Hormuz',lat:26.57,lon:56.25,risk:'ENERGY'},
 {name:'Bab el-Mandeb',lat:12.58,lon:43.33,risk:'RED SEA'},
 {name:'Suez Canal',lat:30.45,lon:32.35,risk:'EUROPE-ASIA'},
 {name:'Strait of Malacca',lat:2.7,lon:101.1,risk:'ASIA'},
 {name:'Panama Canal',lat:9.08,lon:-79.68,risk:'AMERICAS'}
];

const shipIcon=(course=0)=>L.divIcon({
 className:'night-ship-icon',
 html:`<div style="transform:rotate(${Number(course)||0}deg)">▲</div>`,
 iconSize:[18,18],iconAnchor:[9,9]
});

function Recenter({vessel}){const map=useMap();React.useEffect(()=>{if(vessel?.lat!=null&&vessel?.lon!=null)map.flyTo([vessel.lat,vessel.lon],8,{duration:.7})},[vessel,map]);return null}

function classify(v){const t=String(v.type||v.shipType||v.status||'').toLowerCase();const n=String(v.name||'').toLowerCase();if(t.includes('tanker')||n.includes('tanker'))return'TANKER';if(t.includes('cargo')||t.includes('container')||n.includes('container'))return'CARGO';return'OTHER'}

export default function ShippingMap({shipping}){
 const vessels=useMemo(()=>(shipping?.vessels||[]).filter(v=>Number.isFinite(Number(v.lat))&&Number.isFinite(Number(v.lon))),[shipping]);
 const[selected,setSelected]=useState(null),[filter,setFilter]=useState('ALL');
 const visible=vessels.filter(v=>filter==='ALL'||classify(v)===filter);
 return <div className="shippingMapWrap">
  <div className="shippingMapToolbar"><div><b>LIVE AIS MAP</b><small>{visible.length} plotted / {shipping?.count??0} reported</small></div><div className="shipFilters">{['ALL','TANKER','CARGO','OTHER'].map(x=><button key={x} className={filter===x?'on':''} onClick={()=>setFilter(x)}>{x}</button>)}</div></div>
  <MapContainer center={[20,35]} zoom={2} minZoom={2} scrollWheelZoom className="shippingMap">
   <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>
   <LayersControl position="topright">
    <LayersControl.Overlay checked name="Live vessels"><LayerGroup>{visible.map((v,i)=><Marker key={`${v.mmsi||'v'}-${i}`} position={[Number(v.lat),Number(v.lon)]} icon={shipIcon(v.course)} eventHandlers={{click:()=>setSelected(v)}}><Tooltip direction="top" offset={[0,-8]}>{v.name||v.mmsi||'Unknown vessel'}</Tooltip><Popup><div className="shipPopup"><b>{v.name||'Unknown vessel'}</b><span>MMSI {v.mmsi||'—'}</span><span>Speed {v.speed!=null?`${v.speed} kn`:'—'}</span><span>Course {v.course!=null?`${v.course}°`:'—'}</span><span>Status {v.status||'—'}</span><span>Destination {v.destination||'—'}</span></div></Popup></Marker>)}</LayerGroup></LayersControl.Overlay>
    <LayersControl.Overlay checked name="Strategic chokepoints"><LayerGroup>{chokePoints.map(p=><CircleMarker key={p.name} center={[p.lat,p.lon]} radius={7} pathOptions={{weight:2,fillOpacity:.25}}><Tooltip permanent={false}>{p.name} · {p.risk}</Tooltip><Popup><b>{p.name}</b><br/>{p.risk} corridor</Popup></CircleMarker>)}</LayerGroup></LayersControl.Overlay>
   </LayersControl>
   <Recenter vessel={selected}/>
  </MapContainer>
  <div className="shippingMapFooter"><span>Source: {shipping?.source||'AIS feed'}</span><span>Auto-refresh: 30s</span><span>Coverage depends on contributing AIS receivers</span></div>
 </div>
}
