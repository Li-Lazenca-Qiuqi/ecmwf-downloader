import { useId } from 'react'
import world from '../../assets/world-land.json'

type Range = { n: number; w: number; s: number; e: number }
type Extent = { n: number; w: number; s: number; width: number }
const WORLD = { n: 90, w: -180, s: -90, width: 360 }
const outlines = world.paths.map((path, index) => <path key={index} d={path} />)
const longitude = (value: number) => ((value + 180) % 360 + 360) % 360 - 180
const coordinate = (value: number, latitude: boolean) => {
  const normalized = latitude ? value : longitude(value)
  return Math.abs(Number(normalized.toFixed(2))) + '°' + (normalized === 0 ? '' : latitude ? normalized > 0 ? 'N' : 'S' : normalized > 0 ? 'E' : 'W')
}
const ticks = (start: number, end: number, step: number) => Array.from({ length: Math.floor((end - Math.ceil(start / step) * step) / step) + 1 }, (_, index) => (Math.ceil(start / step) + index) * step)

export default function GeoReferenceMap({ kind, coordinates, range = { n: 90, w: -180, s: -90, e: 180 }, global = false }: {
  kind: 'area' | 'location'; coordinates?: unknown; range?: Range; global?: boolean
}) {
  const id = useId().replaceAll(':', '')
  const values = Array.isArray(coordinates) && coordinates.length === (kind === 'location' ? 2 : 4) && coordinates.every((item) => typeof item === 'number' && Number.isFinite(item)) ? coordinates as number[] : undefined
  let selection: Extent | undefined
  if (values) {
    const [north, west, south = north, east = west] = values
    if (north <= range.n && north >= range.s && south <= north && south >= range.s && west >= range.w && west <= range.e && east >= range.w && east <= range.e) {
      const width = kind === 'location' ? 0 : Math.abs(east - west) >= 360 ? 360 : (east - west + 360) % 360
      selection = { n: north, w: width === 360 ? -180 : longitude(west), s: south, width }
    }
  }
  const view = WORLD
  const height = view.n - view.s
  const step = 60
  const font = view.width / 64
  const label = global ? 'Global extent' : selection ? kind === 'location'
    ? coordinate(selection.n, true) + ' · ' + coordinate(selection.w, false)
    : 'North ' + coordinate(selection.n, true) + ' · West ' + coordinate(selection.w, false) + ' · South ' + coordinate(selection.s, true) + ' · East ' + coordinate(selection.w + selection.width, false)
    : 'Coordinate reference'
  return <figure className="geo-reference" aria-label="经纬度参考地图">
    <div className="geo-map-heading"><span>位置参考</span></div>
    <svg className="geo-map" viewBox={[view.w, -view.n, view.width, height].join(' ')} role="img" aria-label={label} data-projection="equirectangular">
      <title>{label}</title>
      <defs><clipPath id={id + '-clip'}><rect x={view.w} y={-view.n} width={view.width} height={height} /></clipPath></defs>
      <g clipPath={'url(#' + id + '-clip)'}>
        <rect className="map-ocean" x={view.w} y={-view.n} width={view.width} height={height} />
        {[-360, 0, 360].map((offset) => <g className="map-land" key={offset} transform={'translate(' + offset + ' 0)'}>{outlines}</g>)}
        <g className="map-grid">{ticks(view.w, view.w + view.width, step).map((lon) => <line key={'lon' + lon} x1={lon} x2={lon} y1={-view.n} y2={-view.s} />)}{ticks(view.s, view.n, step / 2).map((lat) => <line key={'lat' + lat} x1={view.w} x2={view.w + view.width} y1={-lat} y2={-lat} />)}</g>
        {global && <rect className="map-selection" x={-180} y={-90} width={360} height={180} />}
        {selection && [-360, 0, 360].map((offset) => <g key={'selected' + offset}>
          {kind === 'area' && <rect className="map-selection" data-coordinates={[selection.n, selection.w, selection.s, selection.w + selection.width].join(',')} x={selection.w + offset} y={-selection.n} width={selection.width} height={selection.n - selection.s} />}
          {(kind === 'location' || selection.width < view.width / 100) && <circle className="map-marker" cx={selection.w + selection.width / 2 + offset} cy={-(selection.n + selection.s) / 2} r={view.width / 180} />}
        </g>)}
        <g className="map-labels" fontSize={font}>{ticks(view.w + step / 4, view.w + view.width - step / 4, step).map((lon) => <text key={lon} x={lon} y={-view.s - font / 2} textAnchor="middle">{coordinate(lon, false)}</text>)}{ticks(view.s + step / 8, view.n - step / 8, step / 2).map((lat) => <text key={lat} x={view.w + font / 2} y={-lat - font / 3}>{coordinate(lat, true)}</text>)}</g>
      </g>
    </svg>
    <figcaption><span>{label}</span><span>Plate carrée · <a href={world.licence_url} target="_blank" rel="noreferrer">Natural Earth</a> 1:110m</span></figcaption>
  </figure>
}
