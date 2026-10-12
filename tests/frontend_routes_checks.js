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
state.info = { user: { permissions: ['admin|all'], isRegistered: true } };
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

// Date grouping uses event dates/times, not API insertion order or sales deadlines.
const referenceNow = new Date('2026-10-12T12:00:00').getTime();
const datedEvents = [
    { _id: 'past-old', begin_date: '2020-01-01' },
    { _id: 'future-later', begin_date: '2026-10-14', begin_time: '09:00:00' },
    { _id: 'undated' },
    { _id: 'past-recent', begin_date: '2026-10-11' },
    { _id: 'future-near', begin_date: '2026-10-13', begin_time: '09:00:00' },
    { _id: 'today', begin_date: '2026-10-12' },
    { _id: 'ended-today', begin_date: '2026-10-12', begin_time: '08:00:00', end_date: '2026-10-12', end_time: '11:00:00' },
    { _id: 'ongoing', begin_date: '2026-10-10', end_date: '2026-10-12' },
    { _id: 'invalid', begin_date: 'not-a-date' },
    { _id: 'invalid-calendar', begin_date: '2026-02-30' },
];
const grouped = groupEvents(datedEvents, referenceNow);
assert(grouped.upcoming.map(event => event._id).join(',') === 'ongoing,today,future-near,future-later', 'Upcoming/current ordering wrong');
assert(grouped.past.map(event => event._id).join(',') === 'ended-today,past-recent,past-old', 'Past ordering wrong');
assert(grouped.undated.map(event => event._id).join(',') === 'undated,invalid,invalid-calendar', 'Missing/invalid dates were lost');
assert(datedEvents[0]._id === 'past-old', 'Grouping mutated API insertion order');
assert(eventTimestamp('2026-10-12T10:00:00+02:00') === Date.parse('2026-10-12T08:00:00Z'), 'Explicit timezone offset lost');
assert(eventTimestamp('2026-10-12') === new Date(2026, 9, 12).getTime(), 'Date-only start interpreted as UTC');
assert(eventTimestamp('2026-10-12', '', true) === new Date(2026, 9, 13).getTime(), 'Date-only end excludes its date');
assert(groupEvents([{ begin_date: '2026-10-12', end_date: '2026-10-12', end_time: '12:00:00' }], referenceNow).past.length === 1,
    'Exact end boundary is not past');
assert(groupEvents([{ begin_date: '2026-10-12' }], new Date('2026-10-13T00:00:00').getTime()).past.length === 1,
    'No-end event did not expire at local midnight');
assert(formatDate('not-a-date') === '', 'Invalid date breaks event-list rendering');

fixture = { events: [
    { _id: 'past', title: 'Past fixture', begin_date: '2000-01-01' },
    { _id: 'later', title: 'Later fixture', begin_date: '2099-12-01', summary: 'find this event' },
    { _id: 'missing', title: 'Undated fixture' },
    { _id: 'near', title: 'Nearest fixture', begin_date: '2099-01-01' },
    { _id: 'bad', title: 'Invalid fixture', begin_date: 'bad-date' },
] };
await showEvents();
assert(state.events.map(event => event._id).join(',') === 'near,later,past,missing,bad', 'Rendered order is not grouped');
assert([...app.querySelectorAll('.event h2')].map(heading => heading.textContent).join(',') ===
    'Nearest fixture,Later fixture,Past fixture,Undated fixture,Invalid fixture', 'Cards do not follow grouped order');
qs('#event-search').value = 'find this event';
qs('#event-search').dispatchEvent(new Event('input'));
const visibleCards = [...app.querySelectorAll('.event')].filter(card => getComputedStyle(card).display !== 'none');
assert(visibleCards.length === 1 && visibleCards[0].textContent.includes('Later fixture'), 'Search mapped to the wrong sorted event');
assert([...app.querySelectorAll('.event-group')].filter(group => !group.hidden).length === 1, 'Empty groups remain visible after search');
qs('#event-search').value = '';
qs('#event-search').dispatchEvent(new Event('input'));
assert([...app.querySelectorAll('.event')].every(card => !card.hidden), 'Clearing search did not restore past/undated cards');
fixture = { events: [] };
await showEvents();
assert(app.textContent.includes('No events yet.'), 'Empty-list guidance lost');

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

// Guests can register, but receive confirmation without an inaccessible edit redirect.
state.info.user = { permissions: [] };
fixture = { ...eventFixture, ticket: { _id: 'guest-ticket' } };
await showTicketForm(safeId, null);
assert(app.textContent.includes('before registering'), 'Missing guest account guidance');
const guestHash = location.hash;
mutations.length = 0;
qs('#ticket-form').dispatchEvent(new Event('submit', { cancelable: true }));
await settleActions();
assert(mutations.length === 1 && mutations[0].method === 'POST', 'Guest registration failed');
assert(app.querySelector('.page-heading h1').textContent === 'Registration complete', 'Guest confirmation missing');
assert(location.hash === guestHash, 'Guest was redirected to an inaccessible ticket');
assert(!app.querySelector('a[href*="/ticket/"]'), 'Guest confirmation offers ticket access');
state.info.user = { permissions: ['admin|all'], isRegistered: true };

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

// API error text is data, including markup received in a JSON response.
const hostileMessage = '<img src=x onerror="window.injected=true"><script>window.injected=true</script>';
errorPage(new Error(hostileMessage));
assert(app.querySelector('.error p').textContent === hostileMessage, 'Error message data changed');
assert(!app.querySelector('img, script, [onerror]'), 'Injected error page');
notice(hostileMessage, 'error');
assert(notices.lastElementChild.textContent === hostileMessage, 'Notice message data changed');
assert(!notices.querySelector('img, script, [onerror]'), 'Injected error notice');
assert(!window.injected, 'Error message executed code');
