export const sources = { cds: 'CDS · Copernicus', ncar: 'NCAR AWS ERA5', gdex: 'NCAR GDEX ERA5' }
export const sourceOptions = Object.entries(sources).map(([value, label]) => ({ value: value as keyof typeof sources, label }))
export const splitOptions = [
  { value: 'none', label: '不拆分' },
  { value: 'year', label: '按年' },
  { value: 'month', label: '按月' },
  { value: 'day', label: '按日' },
  { value: 'smart', label: '按份数智能拆分' },
]

export const requestSchemaFreshMs = 300_000
export const requestSchemaKey = (datasetId: string, prefix: string) => ['request-schema', datasetId, prefix] as const
