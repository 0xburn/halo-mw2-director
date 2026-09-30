export class BurstWeapon {
  constructor({ magazine = 36, reserve = 108, burst = 3, interval = 0.075, cooldown = 0.45, reload = 2.2 } = {}) {
    Object.assign(this, { magazine, reserve, burst, interval, cooldown, reloadDuration: reload });
    this.ammo = magazine;
    this.time = 0;
    this.readyAt = 0;
    this.reloadEnd = null;
    this.queue = [];
    this.totalShots = 0;
  }
  trigger() {
    if (this.reloadEnd !== null || this.queue.length || this.time + 1e-9 < this.readyAt || !this.ammo) return false;
    for (let i = 0; i < Math.min(this.burst, this.ammo); i++) this.queue.push(this.time + i * this.interval);
    this.readyAt = this.time + this.cooldown;
    return true;
  }
  reload() {
    if (this.reloadEnd !== null || this.queue.length || this.ammo === this.magazine || !this.reserve) return false;
    this.reloadEnd = this.time + this.reloadDuration;
    return true;
  }
  update(dt) {
    if (!Number.isFinite(dt) || dt < 0) throw new Error('Invalid weapon timestep');
    this.time += dt;
    let shots = 0;
    while (this.queue.length && this.queue[0] <= this.time + 1e-9) {
      this.queue.shift();
      if (this.ammo > 0) { this.ammo--; shots++; this.totalShots++; }
    }
    if (this.reloadEnd !== null && this.time >= this.reloadEnd) {
      const count = Math.min(this.magazine - this.ammo, this.reserve);
      this.ammo += count;
      this.reserve -= count;
      this.reloadEnd = null;
    }
    return shots;
  }
}
