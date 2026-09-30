"""Readable authoring compiles to the existing native v2 input timeline."""
import copy
import json
import math
from pathlib import Path
import wave

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'local-assets/halo/native'
ZONE = ROOT / 'local-assets/mw2/Call of Duty Modern Warfare 2/zone/english'
BUTTONS = {'fire': 1, 'sprint': 2, 'reload': 16, 'crouch': 512, 'jump': 1024, 'scope': 2048}
SOUNDS = ('triple-kill', 'warthog-engine', 'warthog-impact', 'warthog-splat', 'halo-splat',
          'chief-death', 'halo-vehicle-impact', 'rocket-fire', 'plasma-fire', 'plasma-explosion', 'plasma-fuse')


class SceneError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise SceneError(message)


def read(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise SceneError(f'{path}: {error}') from error


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def vector(value, size=3):
    return isinstance(value, list) and len(value) == size and all(finite(x) for x in value)


def compile_scene(document):
    if document.get('version') == 2:
        return copy.deepcopy(document)
    require(document.get('format') == 'director/1', 'Expected native version 2 or format director/1')
    require(set(document) <= {'format', 'template', 'title', 'roles', 'actors'}, 'Unknown recipe field')
    name = document.get('template', '')
    require(isinstance(name, str) and name and Path(name).name == name, 'Invalid template name')
    scene = read(ROOT / 'director/templates' / f'{name}.native.json')
    scene['title'] = document.get('title', scene['title'])
    actors = {a['id']: a for a in scene['actors']}
    roles = document.get('roles', {})

    def resolve(role):
        identity = roles.get(role) if isinstance(role, str) else role
        require(type(identity) is int and identity in actors, f'Unknown actor/role: {role!r}')
        return identity

    for role in roles:
        resolve(role)
    for role, edits in document.get('actors', {}).items():
        actor = actors[resolve(role)]
        require(set(edits) <= {'actions', 'route', 'name'}, f'{role}: unsupported actor override')
        for key in ('route', 'name'):
            if key in edits:
                actor[key] = copy.deepcopy(edits[key])
        if 'actions' not in edits:
            continue
        actor['aim'], actor['buttons'] = [], []
        for action in edits['actions']:
            kind = action.get('do')
            common = {'do', 'from', 'to'}
            aim_keys = {'target', 'point', 'height', 'turn_speed', 'response', 'offset_x', 'offset_z'}
            if kind in BUTTONS:
                require(set(action) <= common, f'{role}: unknown field for {kind}')
                actor['buttons'].append([action['from'], action['to'], BUTTONS[kind]])
                continue
            require(kind in ('look', 'quickscope', 'reveal'), f'{role}: unknown action {kind!r}')
            allowed = common | aim_keys
            if kind == 'quickscope':
                allowed |= {'at', 'acquire', 'ads', 'release', 'shot_end'}
            elif kind == 'reveal':
                allowed |= {'ads'}
            require(set(action) <= allowed, f'{role}: unknown field for {kind}')
            start = action.get('acquire', action.get('from'))
            end = action.get('release', action.get('to'))
            require(finite(start) and finite(end), f'{role}: {kind} needs start/end times')
            aim = {'start': start, 'end': end}
            require(('target' in action) != ('point' in action), f'{role}: choose target OR point')
            if 'target' in action:
                aim['actor'] = resolve(action['target'])
            else:
                aim['point'] = action['point']
            for key in aim_keys - {'target', 'point'}:
                if key in action:
                    aim[key] = action[key]
            actor['aim'].append(aim)
            if kind in ('quickscope', 'reveal'):
                ads = action.get('ads')
                require(finite(ads) and start <= ads < end, f'{role}: ADS must fit the aim interval')
                actor['buttons'].append([ads, end, 2048 | 8192])
            if kind == 'quickscope':
                shot, shot_end = action.get('at'), action.get('shot_end', end)
                require(finite(shot) and finite(shot_end) and ads <= shot < shot_end <= end,
                        f'{role}: shot must fit the ADS interval')
                actor['buttons'].append([shot, shot_end, 1])
        actor['aim'].sort(key=lambda cue: cue['start'])
        actor['buttons'].sort(key=lambda cue: cue[0])
    return scene


def validate(scene):
    require(scene.get('version') == 2, 'Native scene version must be 2')
    duration = scene.get('duration')
    require(finite(duration) and 0 < duration <= 600, 'Duration must be 0–600 seconds')
    require(type(scene.get('health', 30)) is int and 0 < scene.get('health', 30) <= 10000, 'Health must be a positive integer')
    actors = scene.get('actors')
    require(isinstance(actors, list) and 1 <= len(actors) <= 16, 'Native v2 supports 1–16 cast slots')
    ids = [a.get('id') for a in actors]
    require(all(type(i) is int for i in ids) and sorted(ids) == list(range(len(ids))),
            'Actor IDs must be unique contiguous slots starting at 0; sparse slots cannot spawn correctly')
    warnings = []

    def interval(start, end, where):
        require(finite(start) and finite(end) and 0 <= start < end <= duration + .001,
                f'{where}: invalid time interval {start!r}–{end!r}')

    def route(rows, where):
        require(isinstance(rows, list) and len(rows) >= 2, f'{where}: at least two route keys required')
        require(all(vector(row, 4) for row in rows), f'{where}: route keys must be [time,x,y,z], all finite')
        require(rows[0][0] == 0 and rows[-1][0] >= duration,
                f'{where}: route must cover the whole take from time zero')
        require(all(b[0] > a[0] for a, b in zip(rows, rows[1:])), f'{where}: route times must increase')
        if where != 'vehicle' and any(math.dist(a[1:3], b[1:3]) / (b[0]-a[0]) > 375 for a, b in zip(rows, rows[1:])):
            warnings.append(f'{where}: a route segment exceeds 375 inches/s; check native reachability')

    def target(cue, key, where):
        if key in cue:
            require(type(cue[key]) is int and cue[key] in ids, f'{where}: unknown {key} {cue[key]}')
        for key in ('point', 'offset', 'origin'):
            if key in cue:
                require(vector(cue[key]), f'{where}: {key} must be a finite xyz vector')

    for actor in actors:
        label = f'actor {actor["id"]}'
        require(isinstance(actor.get('name'), str) and actor['name'], f'{label}: name missing')
        require(isinstance(actor.get('weapon'), str) and actor['weapon'], f'{label}: weapon missing')
        for unsupported in ('character', 'model', 'team'):
            require(unsupported not in actor, f'{label}: v2 ignores {unsupported}; asset selection is still slot-based')
        route(actor.get('route'), label)
        require(finite(actor.get('yaw', 90)), f'{label}: yaw must be finite')
        for cue in actor.get('aim', []):
            interval(cue.get('start'), cue.get('end'), label + ' aim')
            require(('actor' in cue) != ('point' in cue), f'{label}: aim needs actor OR point')
            target(cue, 'actor', label)
        for cue in actor.get('buttons', []):
            require(vector(cue), f'{label}: buttons must be [start,end,mask]')
            interval(cue[0], cue[1], label + ' buttons')
            require(type(cue[2]) is int and cue[2] > 0 and cue[2] & ~sum(BUTTONS.values(), 8192 | 16384) == 0,
                    f'{label}: unsupported button mask {cue[2]}')
        for allowed in actor.get('damage_from', []):
            require(type(allowed) is int and allowed in ids, f'{label}: unknown damage source {allowed}')
    if 'vehicle' in scene:
        route(scene['vehicle'].get('route'), 'vehicle')
        require(15 in ids, 'Current Warthog implementation requires driver slot 15')
        warnings.append('Vehicle uses an authored path; no obstacle/turn-radius validation yet')
    for section in ('battle', 'events', 'camera_cuts'):
        cues = scene.get(section, [])
        times = [cue.get('at') for cue in cues]
        require(all(finite(t) and 0 <= t <= duration for t in times), f'{section}: invalid cue time')
        require(times == sorted(times), f'{section}: cues must be sorted by time')
        for cue in cues:
            for key in ('actor', 'target', 'follow_actor', 'respawn_actor'):
                target(cue, key, section)
            if section == 'battle':
                require(cue.get('kind') in ('plasma', 'grenade', 'rocket', 'native_rocket', 'near_miss', 'engine'),
                        f'Unsupported battle cue: {cue.get("kind")}')
                for key in ('flight', 'fuse'):
                    if key in cue:
                        require(finite(cue[key]) and cue[key] > 0, f'{section}: {key} must be positive')
            if section == 'camera_cuts':
                require(vector(cue.get('eye')) and vector(cue.get('focus')), 'Camera needs finite eye/focus vectors')
                require(cue['eye'] != cue['focus'], 'Camera eye and focus must differ')
                require(finite(cue.get('fov', 58)) and 1 <= cue.get('fov', 58) < 179, 'Invalid camera FOV')
    warnings.append('Geometry, muzzle sightlines, animation and outcomes require a native rehearsal; static checks do not prove them')
    return warnings


def doctor(scene):
    map_name = scene.get('map', 'mp_rust')
    require(isinstance(map_name, str) and Path(map_name).name == map_name, 'Invalid map identifier')
    require((ZONE / f'{map_name}.ff').is_file(), f'Missing native MW2 map: {map_name}')
    checked = []
    for name in ('chief', 'sniper', 'warthog', 'plasma_grenade', 'rocket_projectile', 'plasma_pistol', 'rocket'):
        pack = read(PACK / f'{name}.json')
        n = len(pack.get('positions', []))
        require(0 < n <= 100000, f'{name}: invalid vertex count')
        for key, size in (('positions', 3), ('normals', 3), ('uvs', 2), ('joints', 4), ('weights', 4)):
            rows = pack.get(key, [])
            require(len(rows) == n and all(vector(row, size) for row in rows), f'{name}: invalid {key}')
        require(all(type(i) is int and 0 <= i < n for i in pack['indices']), f'{name}: invalid mesh indices')
        require(len(pack['indices']) % 3 == 0, f'{name}: indices must form triangles')
        ranges = pack.get('ranges', [])
        require(len(ranges) == len(pack.get('materials', [])) and ranges, f'{name}: material/surface mismatch')
        require(all(vector(row, 4) and all(type(v) is int and v >= 0 for v in row)
                    and row[0]+row[1] <= n and row[2]+row[3] <= len(pack['indices']) for row in ranges),
                f'{name}: invalid surface ranges')
        require(all(type(j) is int and 0 <= j < 83 for row in pack['joints'] for j in row), f'{name}: unsupported rig joint')
        require(all(all(w >= 0 for w in row) and abs(sum(row)-1) <= .01 for row in pack['weights']), f'{name}: invalid skin weights')
        vertices = PACK / ('vertices.bin' if name == 'chief' else f'{name}-vertices.bin')
        require(vertices.exists() and vertices.stat().st_size == n * 32, f'{name}: packed vertex data missing/wrong size')
        for material in pack['materials']:
            file = material['file']
            require(Path(file).name == file and '\\' not in file, f'{name}: invalid texture filename')
            path = PACK / file
            require(path.exists() and path.stat().st_size == material['width'] * material['height'] * 4,
                    f'{name}: texture missing/wrong RGBA size: {file}')
        checked.append(name)
    for name in SOUNDS:
        path = PACK / f'{name}.wav'
        try:
            with wave.open(str(path), 'rb') as audio:
                require(audio.getcomptype() == 'NONE' and audio.getnframes() > 0,
                        f'{name}: empty/unsupported PCM audio')
                require(audio.getnchannels() in (1, 2) and audio.getsampwidth() == 2,
                        f'{name}: expected mono/stereo 16-bit PCM')
        except (OSError, wave.Error, EOFError) as error:
            raise SceneError(f'{name}: {error}') from error
    return {'map': map_name, 'mesh_packs_checked': checked, 'sound_files_checked': len(SOUNDS),
            'map_status': 'rehearsed with accepted take' if map_name == 'mp_rust' else 'installed, native compatibility unverified'}


def describe(scene):
    return {'title': scene.get('title'), 'map': scene.get('map', 'mp_rust'), 'duration': scene['duration'],
            'actors': [{'id': a['id'], 'name': a['name'], 'weapon': a['weapon'],
                        'visual': 'Halo CE Chief' if a['id'] >= 8 else 'MW2 soldier',
                        'route_keys': len(a['route']), 'aim_cues': len(a['aim']), 'input_cues': len(a['buttons'])}
                       for a in scene['actors']],
            'effects': {kind: sum(cue['kind'] == kind for cue in scene.get('battle', []))
                        for kind in sorted({cue['kind'] for cue in scene.get('battle', [])})},
            'camera_cuts': scene.get('camera_cuts', []),
            'limits': ['16 cast slots', 'character selection tied to slots 0–7 / 8–15',
                       'camera cuts currently activate after local-player death',
                       'high-level actions compile to timed inputs, not reactive combat behaviors']}


def write_scene(path, scene):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(scene, indent=2) + '\n')
    temporary.replace(path)
    return path
