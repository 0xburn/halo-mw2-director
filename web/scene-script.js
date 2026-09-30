// Scene state is sampled from absolute time, so seeking and camera retakes agree.
export const WEAPONS = {
  intervention: { label: 'MW2 Intervention', magazine: 5, burst: 1, interval: .1, cooldown: 1.1, reload: 2.8 },
  pistol: { label: 'CE pistol', magazine: 12, burst: 1, interval: .1, cooldown: .3, reload: 1.8 },
  sniper: { label: 'CE sniper', magazine: 4, burst: 1, interval: .1, cooldown: .8, reload: 2.5 },
  rocket: { label: 'CE rocket launcher', magazine: 2, burst: 1, interval: .1, cooldown: 1, reload: 3 },
  rifle: { label: 'Burst rifle', magazine: 36, burst: 3, interval: .075, cooldown: .45, reload: 2.2 }
};
const vec = v => Array.isArray(v) && v.length === 3 && v.every(Number.isFinite);
const lerp = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
const clamp = t => Math.max(0, Math.min(1, t));
const require = (ok, message) => { if (!ok) throw new Error(message); };
const copy = v => JSON.parse(JSON.stringify(v));

export function compileScene(input) {
  const spec = copy(input);
  require(spec.version === 1, 'Scene version must be 1');
  require(Number.isFinite(spec.duration) && spec.duration > 0 && spec.duration <= 300, 'Duration must be 0–300 seconds');
  require(Array.isArray(spec.teams) && spec.teams.length > 0, 'Add at least one team');
  const actors = [], teams = new Set();
  for (const team of spec.teams) {
    require(typeof team.id === 'string' && /^[a-z][a-z0-9_]*$/i.test(team.id) && !teams.has(team.id), 'Team IDs must be unique words');
    teams.add(team.id);
    require(Number.isInteger(team.count) && team.count >= 0 && team.count <= 64, `${team.id}: count must be 0–64`);
    require(vec(team.origin) && vec(team.spacing ?? [2, 0, 0]), `${team.id}: origin and spacing must be [x,y,z]`);
    require(Object.hasOwn(WEAPONS, team.weapon ?? 'pistol'), `${team.id}: unknown weapon`);
    require(['chief', 'soldier'].includes(team.model ?? 'chief'), `${team.id}: unknown character model`);
    require(team.yaw === undefined || Number.isFinite(team.yaw), `${team.id}: yaw must be radians`);
    require(team.color === undefined || /^#[0-9a-f]{6}$/i.test(team.color), `${team.id}: color must be #rrggbb`);
    for (let i = 0; i < team.count; i++) {
      actors.push({ id: `${team.id}-${i + 1}`, team: team.id, model: team.model ?? 'chief', color: team.color ?? '#91ac66', weapon: team.weapon ?? 'pistol',
        origin: team.origin.map((v, j) => v + (team.spacing ?? [2, 0, 0])[j] * i), yaw: team.yaw ?? 0, actions: [] });
    }
  }
  require(actors.length > 0 && actors.length <= 128, 'Use 1–128 actors in total');
  const ids = new Set(actors.map(a => a.id));
  const targetOK = t => vec(t) || (typeof t === 'string' && ids.has(t));
  require(Array.isArray(spec.actions ?? []), 'Actions must be an array');
  require((spec.actions ?? []).length <= 2000, 'Maximum 2,000 actions');
  const events = [], types = new Set(['move', 'aim', 'fire', 'jump', 'die', 'respawn']);
  for (const action of (spec.actions ?? []).sort((a, b) => a.at - b.at)) {
    require(Number.isFinite(action.at) && action.at >= 0 && action.at <= spec.duration, 'Action time is outside scene');
    require(types.has(action.type), `Unknown action: ${action.type}`);
    const selected = actors.filter(a => action.actor === '*' || action.actor === a.team || action.actor === a.id);
    require(selected.length > 0, `No actors match: ${action.actor}`);
    if (['move', 'jump'].includes(action.type)) {
      require(Number.isFinite(action.duration) && action.duration > 0 && action.at + action.duration <= spec.duration, 'Movement/jump duration is outside scene');
    }
    if (action.type === 'move') require(vec(action.to) !== vec(action.by), 'Move needs exactly one of to or by: [x,y,z]');
    if (action.type === 'jump') require(Number.isFinite(action.height) && action.height > 0, 'Jump needs a positive height');
    if (['fire', 'aim'].includes(action.type)) require(targetOK(action.target), 'Aim/fire target must be an actor ID or [x,y,z]');
    if (action.type === 'respawn') require(action.position === undefined || vec(action.position), 'Respawn position must be [x,y,z]');
    if (action.type === 'fire') {
      require(Number.isInteger(action.count ?? 1) && (action.count ?? 1) > 0 && (action.count ?? 1) <= 100, 'Fire count must be 1–100');
      require(Number.isFinite(action.every ?? 1) && (action.every ?? 1) > 0, 'Fire every must be positive seconds');
    }
    for (const actor of selected) {
      const a = { ...action };
      if (a.type === 'move') {
        const prior = actor.actions.filter(x => x.type === 'move').at(-1);
        require(!prior || prior.at + prior.duration <= a.at, `${actor.id}: overlapping moves`);
        a.from = baseState(actor, a.at).position;
        a.to = a.to ?? a.from.map((v, i) => v + a.by[i]);
      }
      if (a.type === 'jump') {
        const prior = actor.actions.filter(x => x.type === 'jump').at(-1);
        require(!prior || prior.at + prior.duration <= a.at, `${actor.id}: overlapping jumps`);
      }
      if (a.type === 'fire') {
        const preset = WEAPONS[actor.weapon], every = a.every ?? Math.max(1, preset.cooldown);
        require(every >= preset.cooldown, `${actor.id}: fire interval is below weapon cooldown`);
        for (let i = 0; i < (a.count ?? 1); i++) for (let shot = 0; shot < preset.burst; shot++) {
          const at = a.at + i * every + shot * preset.interval;
          require(at <= spec.duration, `${actor.id}: shot falls after scene end`);
          events.push({ at, actor: actor.id, target: a.target, weapon: actor.weapon });
        }
      }
      actor.actions.push(a);
    }
  }
  require(events.length <= 20000, 'Maximum 20,000 shots per scene');
  require(Array.isArray(spec.camera) && spec.camera.length > 0, 'Add camera keyframes');
  spec.camera.sort((a, b) => a.at - b.at);
  for (const [i, frame] of spec.camera.entries()) {
    require(Number.isFinite(frame.at) && frame.at >= 0 && frame.at <= spec.duration, 'Camera time is outside scene');
    require(i === 0 ? frame.at === 0 : frame.at > spec.camera[i - 1].at, 'Camera begins at 0; keyframe times must be unique');
    require(vec(frame.position) && targetOK(frame.target), 'Camera needs position and target');
    require(frame.fov === undefined || (Number.isFinite(frame.fov) && frame.fov >= 15 && frame.fov <= 110), 'Camera FOV must be 15–110');
    require(frame.pov === undefined || frame.pov === null || ids.has(frame.pov), 'POV must name an actor');
    require(frame.roll === undefined || Number.isFinite(frame.roll), 'Camera roll must be radians');
    require(frame.scope === undefined || typeof frame.scope === 'boolean', 'Scope must be true or false');
  }
  return { spec, actors, events: events.sort((a, b) => a.at - b.at) };
}

function baseState(actor, time) {
  let position = [...actor.origin], yaw = actor.yaw, alive = true, aim = null, moving = false, jump = 0, diedAt = null;
  for (const a of actor.actions) {
    if (a.at > time) break;
    if (a.type === 'move') {
      const u = clamp((time - a.at) / a.duration);
      position = lerp(a.from, a.to, u); moving = u < 1;
      const dx = a.to[0] - a.from[0], dz = a.to[2] - a.from[2];
      if (Math.hypot(dx, dz) > .001) yaw = Math.atan2(-dx, -dz);
    }
    if (a.type === 'aim' || a.type === 'fire') aim = a.target;
    if (a.type === 'die') { alive = false; diedAt = a.at; }
    if (a.type === 'respawn') { alive = true; diedAt = null; position = [...(a.position ?? actor.origin)]; }
    if (a.type === 'jump') jump = time < a.at + a.duration ? 4 * a.height * clamp((time - a.at) / a.duration) * (1 - clamp((time - a.at) / a.duration)) : 0;
  }
  position[1] += jump;
  return { id: actor.id, team: actor.team, model: actor.model, weapon: actor.weapon, position, yaw, alive, diedAt, aim, moving };
}

export function sampleScene(scene, rawTime) {
  const time = Math.max(0, Math.min(scene.spec.duration, rawTime));
  const actors = scene.actors.map(a => baseState(a, time)), lookup = new Map(actors.map(a => [a.id, a]));
  const target = t => typeof t === 'string' ? lookup.get(t).position.map((v, i) => v + (i === 1 ? 1.4 : 0)) : t;
  for (const actor of actors) if (actor.aim) {
    const at = target(actor.aim);
    actor.yaw = Math.atan2(actor.position[0] - at[0], actor.position[2] - at[2]);
  }
  const frames = scene.spec.camera;
  const next = frames.findIndex(f => f.at > time);
  const a = next < 0 ? frames.at(-1) : frames[Math.max(0, next - 1)], b = next < 0 ? a : frames[next];
  let u = a === b || b.cut ? 0 : clamp((time - a.at) / (b.at - a.at));
  u = u * u * (3 - 2 * u);
  return { time, actors, camera: { position: lerp(a.position, b.position, u), target: lerp(target(a.target), target(b.target), u), fov: (a.fov ?? 60) + ((b.fov ?? 60) - (a.fov ?? 60)) * u,
    roll: (a.roll ?? 0) + ((b.roll ?? 0) - (a.roll ?? 0)) * u, pov: a.pov ?? null, scope: a.scope ?? false, caption: a.caption ?? '' } };
}

export function makeDemo(red = 3, blue = 3, weapon = 'pistol', origin = [0, 0, 0]) {
  const p = (x, y, z) => [x + origin[0], y + origin[1], z + origin[2]];
  const teams = [
    { id: 'red', count: red, color: '#d95545', weapon, origin: p(-6, 0, 8), spacing: [0, 0, 2.2], yaw: -Math.PI / 2 },
    { id: 'blue', count: blue, color: '#438de1', weapon, origin: p(6, 0, 8), spacing: [0, 0, 2.2], yaw: Math.PI / 2 }
  ];
  const actions = [];
  for (const [team, count, direction, enemy, enemyCount] of [['red', red, 1, 'blue', blue], ['blue', blue, -1, 'red', red]]) {
    if (!count) continue;
    actions.push({ at: 1, actor: team, type: 'move', by: [direction * 2, 0, 0], duration: 3 });
    if (enemyCount) actions.push({ at: 4, actor: team, type: 'fire', target: `${enemy}-1`, count: 4, every: 1.2 });
    actions.push({ at: 10, actor: `${team}-1`, type: 'jump', height: 2, duration: 1.2 });
  }
  if (blue) actions.push({ at: 8.5, actor: 'blue-1', type: 'die' }, { at: 12, actor: 'blue-1', type: 'respawn' });
  return { version: 1, name: 'Dust-up — CE cast', duration: 16, teams, actions, camera: [
    { at: 0, position: p(0, 6, 23), target: p(0, 1.4, 9), fov: 60 },
    { at: 4, position: p(-9, 3, 16), target: p(1, 1.4, 9), fov: 58 },
    { at: 8, position: p(9, 2.4, 14), target: p(-3, 1.4, 9), fov: 58, cut: true },
    { at: 12, position: p(0, 8, 23), target: p(0, 1.4, 9), fov: 58 },
    { at: 16, position: p(0, 12, 26), target: p(0, 1.4, 9), fov: 60 }
  ] };
}
