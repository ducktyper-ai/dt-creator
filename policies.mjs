// Pure availability derivations for the labelled spike, not installed site adapters.
export function utcAvailability(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(value)) throw new TypeError('Availability must be an explicit UTC timestamp');
  const parsed=new Date(value), normalized=value.includes('.')?value:value.replace('Z','.000Z');
  if (!Number.isFinite(parsed.getTime()) || parsed.toISOString()!==normalized) throw new TypeError('Availability must be a real UTC timestamp');
  return value;
}
const london=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/London',year:'numeric',month:'2-digit',day:'2-digit'});
const londonDay=time=>{
  const fields=Object.fromEntries(london.formatToParts(new Date(time)).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
  return `${fields.year.padStart(4,'0')}-${fields.month}-${fields.day}`;
};
export function londonDateAvailability(label) {
  if(typeof label!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(label))throw new TypeError('London publication label must be YYYY-MM-DD');
  const base=Date.parse(`${label}T00:00:00Z`);
  if(!Number.isFinite(base)||new Date(base).toISOString().slice(0,10)!==label)throw new TypeError('London publication label must be a real date');
  let low=base-36*60*60*1000,high=base+36*60*60*1000;
  if(londonDay(low)>=label||londonDay(high)<label)throw new TypeError('London availability cannot be derived under the current timezone policy');
  while(high-low>1){const mid=Math.floor((low+high)/2);if(londonDay(mid)>=label)high=mid;else low=mid;}
  if(londonDay(high)!==label)throw new TypeError('London publication date is unsupported');
  return new Date(high).toISOString();
}
