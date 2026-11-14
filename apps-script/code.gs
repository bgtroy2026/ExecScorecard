/**
 * Big Grove — Executive Scorecard sign-in backend (Google Apps Script, bound to the "Executive Scorecard Roster" sheet)
 *
 * Its own roster, its own secret: independent of the Store Director Portal and Sales Portal backends.
 *
 * Deploy: Deploy → New deployment → Web app → Execute as: Me → Who has access: Anyone.
 * To UPDATE without changing the URL: Deploy → Manage deployments → Edit → Version: New version → Deploy.
 *
 * Script Properties (Project Settings → Script properties):
 *   EXEC_SECRET — REQUIRED. Same value as "secret" in .exec-secret.json on the Mac (tools/build_bundle.py).
 *   EXEC_EPOCH  — optional, default "1". Same as "epoch" there. Bump BOTH to revoke every key ever handed out.
 *
 * Roster: first tab, headers in row 1: email | name | role   (role: Admin or Leadership — anything else is refused)
 * Sign-ins are logged to a "Logins" tab (auto-created): When | Email | Name | Event
 *
 * Protocol (POST, Content-Type text/plain):
 *   {"a":"signin","t":<Google ID token>} → { ok, profile:{email,name,role}, bundle:{id,key}, sid }
 *   {"a":"refresh","s":<sid>}            → the same, re-checked against the roster today (sid lasts 30 days)
 *   {"a":"usage","s":<sid>}              → Admin only: the Logins log (newest first, up to 2,000 rows) + the roster
 *
 * Every sign-in is logged as "signin", every return visit (a remembered session re-checked) as "open",
 * and refusals as "refused". The usage view on the page reads them back for roster Admins only.
 */
var CLIENT_ID = '169287489700-t5en62nibhp9ttn24vfimd7k974dgl9i.apps.googleusercontent.com';
var SHEET_ID = '1g9rdbN1eT9or3StT_WoH3woguSIkOYvpgv7D27TquJA';
var ALLOWED_DOMAINS = ['biggrovebrewery.com', 'biggrove.com'];
var SESSION_DAYS = 30;

function prop(n) { return PropertiesService.getScriptProperties().getProperty(n); }
function json(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }
function doGet() { return json({ ok: true, service: 'exec-scorecard-login' }); }

function doPost(e) {
  try {
    var req = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    if (req.a === 'signin') return json(signin(String(req.t || '')));
    if (req.a === 'refresh') return json(refresh(String(req.s || '')));
    if (req.a === 'usage') return json(usage(String(req.s || '')));
    return json({ ok: false, error: 'unknown action' });
  } catch (err) { return json({ ok: false, error: 'server error: ' + err }); }
}

function signin(token) {
  if (!token) return { ok: false, error: 'no token' };
  var r = UrlFetchApp.fetch('https://oauth2.googleapis.com/tokeninfo', { method: 'post', payload: { id_token: token }, muteHttpExceptions: true });
  if (r.getResponseCode() !== 200) return { ok: false, error: 'invalid token' };
  var info = JSON.parse(r.getContentText());
  if (info.aud !== CLIENT_ID) return { ok: false, error: 'wrong app' };
  if (Number(info.exp) * 1000 < Date.now()) return { ok: false, error: 'expired token' };
  if (String(info.email_verified) !== 'true') return { ok: false, error: 'unverified email' };
  var email = String(info.email || '').toLowerCase().trim();
  if (ALLOWED_DOMAINS.indexOf(email.split('@')[1] || '') === -1) return { ok: false, error: 'not on the roster' };
  var out = grant(email, String(info.name || ''));
  log(email, out.ok ? out.profile.name : String(info.name || ''), out.ok ? 'signin' : 'refused');
  return out;
}

function refresh(sid) {
  var s = readSid(sid);
  if (!s) return { ok: false, error: 'expired session' };
  var out = grant(s.e, '');
  log(s.e, out.ok ? out.profile.name : '', out.ok ? 'open' : 'refused');
  return out;
}

function usage(sid) {
  var s = readSid(sid);
  if (!s) return { ok: false, error: 'expired session' };
  var g = grant(s.e, '');
  if (!g.ok || !/^admin$/i.test(g.profile.role)) return { ok: false, error: 'admins only' };
  var ss = SpreadsheetApp.openById(SHEET_ID);
  var sh = ss.getSheetByName('Logins');
  var rows = [];
  if (sh && sh.getLastRow() > 1) {
    var n = Math.min(sh.getLastRow() - 1, 2000);
    rows = sh.getRange(sh.getLastRow() - n + 1, 1, n, 4).getValues().reverse().map(function (r) {
      return [r[0] instanceof Date ? r[0].toISOString() : String(r[0]), String(r[1]), String(r[2]), String(r[3])];
    });
  }
  var roster = ss.getSheets()[0].getDataRange().getValues().slice(1).filter(function (r) { return r[0]; })
    .map(function (r) { return [String(r[0]).toLowerCase().trim(), String(r[1] || ''), String(r[2] || '')]; });
  return { ok: true, rows: rows, roster: roster };
}

function grant(email, googleName) {
  var rows = SpreadsheetApp.openById(SHEET_ID).getSheets()[0].getDataRange().getValues();
  var hit = null;
  for (var i = 1; i < rows.length; i++) if (String(rows[i][0]).toLowerCase().trim() === email) { hit = rows[i]; break; }
  if (!hit) return { ok: false, error: 'not on the roster' };
  var role = String(hit[2] || '').trim();
  if (!/^(admin|leadership)$/i.test(role)) return { ok: false, error: 'not on the roster' };
  var secret = prop('EXEC_SECRET');
  if (!secret) return { ok: false, error: 'EXEC_SECRET script property is not set' };
  var salted = 'exec:' + (prop('EXEC_EPOCH') || '1');
  var dig = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, salted, Utilities.Charset.UTF_8);
  var id = dig.map(function (b) { return ('0' + (b & 255).toString(16)).slice(-2); }).join('').slice(0, 16);
  var key = Utilities.base64Encode(Utilities.computeHmacSha256Signature(salted, secret, Utilities.Charset.UTF_8));
  var name = String(hit[1] || googleName || email);
  return { ok: true, profile: { email: email, name: name, role: role }, bundle: { id: id, key: key }, sid: makeSid(email) };
}

function sign(payload) {
  return Utilities.base64EncodeWebSafe(Utilities.computeHmacSha256Signature(payload, 'sid:' + prop('EXEC_SECRET'), Utilities.Charset.UTF_8));
}
function makeSid(email) {
  var p = Utilities.base64EncodeWebSafe(JSON.stringify({ e: email, x: Date.now() + SESSION_DAYS * 864e5 }));
  return p + '.' + sign(p);
}
function readSid(sid) {
  var parts = String(sid || '').split('.');
  if (parts.length !== 2 || sign(parts[0]) !== parts[1]) return null;
  try {
    var s = JSON.parse(Utilities.newBlob(Utilities.base64DecodeWebSafe(parts[0])).getDataAsString());
    return s.x > Date.now() ? s : null;
  } catch (e) { return null; }
}

function log(email, name, ev) {
  try {
    var ss = SpreadsheetApp.openById(SHEET_ID), sh = ss.getSheetByName('Logins');
    if (!sh) { sh = ss.insertSheet('Logins'); sh.appendRow(['When', 'Email', 'Name', 'Event']); }
    sh.appendRow([new Date(), email, name, ev]);
  } catch (e) {}
}
