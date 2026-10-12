// Executed after the active client source in an isolated browser test page.
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const requests = [];
const mutations = [];
let fixture = {};
api = async (path, options = {}) => {
    requests.push(path);
    if (options.method) mutations.push({ path, ...options });
    return fixture;
};
const realConnectUpdates = connectUpdates;
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

// Exercise stored identifiers at the controls, not just the route/link sinks.
const actionId = hostileId + '/?fragment#';
const actionEventId = 'event%22&/other';
window.confirm = () => true;
const settleActions = () => new Promise(resolve => setTimeout(resolve, 0));
window.WebSocket = class extends EventTarget {
    constructor(url) { super(); this.url = url; }
    close() {}
};
connectUpdates = realConnectUpdates;
fixture = { title: 'Test event', tickets: [{ _id: actionId, name: 'Test attendee' }] };
await showTickets(actionEventId);
assertSafeLinks(actionEventId);
let attendance = app.querySelector('[data-attendance]');
let deletion = app.querySelector('[data-delete-ticket]');
assert(attendance.dataset.attendance === actionId, 'Attendance identifier changed by HTML parsing');
assert(deletion.dataset.deleteTicket === actionId, 'Delete identifier changed by HTML parsing');
mutations.length = 0;
attendance.checked = true;
attendance.dispatchEvent(new Event('change'));
await settleActions();
assert(mutations.length === 1 && mutations[0].method === 'PUT', 'Attendance did not submit once');
assert(mutations[0].path === `/events/${encodeURIComponent(actionEventId)}/tickets/${encodeURIComponent(actionId)}`,
    'Attendance API identifier not encoded once');
assert(JSON.parse(mutations[0].body).attended === true, 'Attendance value lost');
mutations.length = 0;
window.confirm = () => false;
deletion.click();
await settleActions();
assert(mutations.length === 0, 'Cancelled deletion submitted');
window.confirm = () => true;
deletion.click();
await settleActions();
assert(mutations.length === 1 && mutations[0].method === 'DELETE', 'Delete did not submit once');
assert(mutations[0].path === `/events/${encodeURIComponent(actionEventId)}/tickets/${encodeURIComponent(actionId)}`,
    'Delete API identifier not encoded once');
assert(location.hash === `#/event/${encodeURIComponent(actionEventId)}/tickets`, 'Delete redirect changed identifier');

for (const update of [
    { action: 'update', _id: actionId, ticket: { _id: actionId, name: 'Updated attendee', attended: true } },
    { action: 'add', ticket: { _id: 'second\"&<ticket>', name: 'Second attendee' } },
    { action: 'delete', _id: actionId },
]) {
    state.socket.dispatchEvent(new MessageEvent('message', { data: JSON.stringify(update) }));
    assert(!app.querySelector('img, [onmouseover], [onerror]'), 'Injected live-update row');
    if (update.action === 'update') {
        assert(app.querySelector('[data-attendance]').checked, 'Live attendance update lost');
        assert(app.querySelector('[data-attendance]').dataset.attendance === actionId, 'Live identifier changed');
    }
    if (update.action === 'add') {
        assert(app.querySelectorAll('[data-attendance]').length === 2, 'Live addition missing');
    }
}
assert(app.querySelectorAll('[data-attendance]').length === 1, 'Live deletion missing');
assert(app.querySelector('[data-attendance]').dataset.attendance === 'second\"&<ticket>', 'Added identifier changed');
qs('#ticket-search').value = 'no match';
qs('#ticket-search').dispatchEvent(new Event('input'));
assert(!app.querySelector('[data-attendance]'), 'Ticket search did not filter');

fixture = { users: [{ _id: actionId, username: 'Test user' }] };
await showUsers();
assertSafeLinks(actionId);
const userDelete = app.querySelector('[data-delete-user]');
assert(userDelete.dataset.deleteUser === actionId, 'User identifier changed by HTML parsing');
mutations.length = 0;
userDelete.click();
await settleActions();
assert(mutations.length === 1 && mutations[0].method === 'DELETE', 'User deletion did not submit once');
assert(mutations[0].path === `/users/${encodeURIComponent(actionId)}`, 'User API identifier not encoded once');
assert(!window.injected, 'Stored identifier executed code');

fixture = { ...eventFixture, ticket: { _id: actionId, name: 'Test attendee' } };
for (const ticketId of [null, actionId]) {
    await showTicketForm(actionEventId, ticketId);
    mutations.length = 0;
    qs('#ticket-form').dispatchEvent(new Event('submit', { cancelable: true }));
    await settleActions();
    assert(mutations.length === 1, 'Ticket form did not submit once');
    assert(mutations[0].method === (ticketId ? 'PUT' : 'POST'), 'Incorrect ticket form method');
    const expectedPath = `/events/${encodeURIComponent(actionEventId)}/tickets`
        + (ticketId ? `/${encodeURIComponent(ticketId)}` : '');
    assert(mutations[0].path === expectedPath, 'Ticket form API identifier not encoded once');
    assert(location.hash === `#/event/${encodeURIComponent(actionEventId)}/ticket/${encodeURIComponent(actionId)}/edit`,
        'Ticket form redirect changed identifier');
}

fixture = { username: 'Test user', email: 'test@example.invalid' };
await showUser(actionId);
mutations.length = 0;
qs('#user-form').dispatchEvent(new Event('submit', { cancelable: true }));
await settleActions();
assert(mutations.length === 1 && mutations[0].method === 'PUT', 'Account form did not submit once');
assert(mutations[0].path === `/users/${encodeURIComponent(actionId)}`, 'Account API identifier not encoded once');

fixture = { ...eventFixture, _id: actionEventId };
await showEvent(actionEventId, true);
mutations.length = 0;
qs('#event-form').dispatchEvent(new Event('submit', { cancelable: true }));
await settleActions();
assert(mutations.length === 1 && mutations[0].method === 'PUT', 'Event form did not submit once');
assert(location.hash === `#/event/${encodeURIComponent(actionEventId)}/edit`, 'Event save redirect changed identifier');
await showNewEvent();
qs('#event-form input[name="title"]').value = 'Created event';
mutations.length = 0;
qs('#event-form').dispatchEvent(new Event('submit', { cancelable: true }));
await settleActions();
assert(mutations.length === 1 && mutations[0].method === 'POST', 'New event did not submit once');
assert(location.hash === `#/event/${encodeURIComponent(actionEventId)}/edit`, 'New event redirect changed identifier');
