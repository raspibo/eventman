// Executed after the active client source in an isolated browser test page.
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const requests = [];
let fixture = {};
api = async path => { requests.push(path); return fixture; };
connectUpdates = () => {};
state.info = { user: { permissions: ['admin|all'] } };
const hostileId = '\" onmouseover=\"window.injected=true\"><img src=x onerror=\"window.injected=true\">\'&%';
const safeId = '1700000000_12-3-abcdef';
const eventFixture = { title: 'Test event', tickets: [{ _id: 'ticket-1', name: 'Test attendee' }] };

function assertSafeLinks(expectedId) {
    assert(!app.querySelector('img, script, [onmouseover], [onerror]'), 'Injected element or handler');
    assert(!window.injected, 'Injected code executed');
    const links = [...app.querySelectorAll('a[href]')];
    assert(links.length > 0, 'Expected navigation links');
    assert(links.some(link => link.getAttribute('href').includes(encodeURIComponent(expectedId))),
        'Identifier was not encoded in navigation');
    for (const link of links) {
        assert(link.attributes.length <= 2, 'Unexpected link attribute');
    }
}

fixture = eventFixture;
await showTickets(hostileId);
assertSafeLinks(hostileId);
assert(app.querySelector('.page-heading .actions a').textContent === 'Add ticket', 'Missing add action');
await showEvent(hostileId, false);
assertSafeLinks(hostileId);
await showTicketForm(hostileId, null);
assertSafeLinks(hostileId);
assert(app.querySelector('#ticket-form'), 'Missing registration form');

fixture = { events: [{ ...eventFixture, _id: hostileId }] };
await showEvents();
assertSafeLinks(hostileId);
fixture = { users: [{ _id: hostileId, username: 'Test user' }] };
state.info.user.permissions = ['users|read'];
await showUsers();
assertSafeLinks(hostileId);
state.info.user.permissions = ['admin|all'];
fixture = { tickets: [{ _id: hostileId, event_id: hostileId, name: 'Test attendee' }] };
await showAllTickets();
assertSafeLinks(hostileId);

state.info.user._id = hostileId;
state.info.user.username = 'Test user';
renderNavigation();
assert(!nav.querySelector('img, [onmouseover], [onerror]'), 'Injected account navigation');
assert(nav.querySelector('a[href^="#/user/"]').getAttribute('href') === `#/user/${encodeURIComponent(hostileId)}/edit`,
    'Incorrect account navigation');

fixture = eventFixture;
for (const id of [safeId, 'événement-²_1']) {
    requests.length = 0;
    location.hash = `#/event/${encodeURIComponent(id)}/tickets`;
    await render();
    assert(requests[0] === `/events/${encodeURIComponent(id)}`, 'Identifier was encoded twice or changed');
    assert(app.querySelector('.page-heading h1').textContent === 'Tickets · Test event', 'Navigation failed');
    assertSafeLinks(id);
}

for (const id of [hostileId, '../outside', 'event/ticket', '%22attack', '', '%']) {
    requests.length = 0;
    location.hash = `#/event/${id === '%' ? '%' : encodeURIComponent(id)}/tickets`;
    await render();
    assert(requests.length === 0, 'Invalid identifier reached API');
    assert(!app.querySelector('img, [onmouseover], [onerror]'), 'Injected malformed route');
    assert(app.querySelector('.error'), 'Expected controlled error page');
}

fixture = eventFixture;
location.hash = `#/event/${safeId}/view`;
await render();
assert(app.querySelector('#event-form fieldset').disabled, 'View form is not read-only');
location.hash = `#/event/${safeId}/edit`;
await render();
assert(!app.querySelector('#event-form fieldset').disabled, 'Edit form is disabled');
assert(!window.injected, 'Injected code executed');
