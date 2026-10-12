const app = document.querySelector('#main');
const nav = document.querySelector('#nav-links');
const notices = document.querySelector('#notices');
const state = { info: {}, event: null, events: [], socket: null };
const defaultFormSchema = {
    formlyFieldsModel: [
        { fieldGroup: ['Name', 'Surname', 'Email'].map(label => ({ key: label.toLowerCase(), type: 'input', templateOptions: { label } })) },
        { fieldGroup: ['Job title', 'Company'].map(label => ({ key: label.toLowerCase(), type: 'input', templateOptions: { label } })) }
    ]
};

const escapeHtml = (value = '') => String(value).replace(/[&<>"']/g, char =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const htmlId = value => escapeHtml(encodeURIComponent(value));
const route = () => location.hash.slice(1) || '/events';

function routeId(value) {
    // Decode once, then enforce the server's identifier character restrictions.
    const id = decodeURIComponent(value || '');
    if (!/^[\p{L}\p{N}_-]+$/u.test(id)) throw new Error('Invalid route identifier.');
    return id;
}
const hasPermission = permission => {
    const permissions = state.info.user?.permissions || [];
    const [scope] = permission.split('|');
    return permissions.includes('admin|all') || permissions.includes(`${scope}|all`) || permissions.includes(permission);
};
const formatDate = value => {
    const timestamp = eventTimestamp(value);
    return timestamp === null ? '' : new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium', timeStyle: value.includes(':') ? 'short' : undefined
    }).format(new Date(timestamp));
};

function eventTimestamp(date, time = '', endOfDay = false) {
    if (typeof date !== 'string') return null;
    const parts = date.match(/^(\d{4})-(\d{2})-(\d{2})(?:$|T)/);
    if (!parts) return null;
    const calendar = new Date(Number(parts[1]), Number(parts[2]) - 1, Number(parts[3]));
    if (calendar.getFullYear() !== Number(parts[1]) || calendar.getMonth() !== Number(parts[2]) - 1
        || calendar.getDate() !== Number(parts[3])) return null;
    const value = time ? `${date.slice(0, 10)}T${time}` : date.length === 10 ? `${date}T00:00:00` : date;
    const parsed = new Date(value);
    if (!Number.isFinite(parsed.getTime())) return null;
    if (endOfDay && date.length === 10 && !time) parsed.setHours(24, 0, 0, 0);
    return parsed.getTime();
}

function groupEvents(events, now = Date.now()) {
    const groups = { upcoming: [], past: [], undated: [] };
    for (const event of events) {
        const start = eventTimestamp(event.begin_date, event.begin_time);
        if (start === null) {
            groups.undated.push(event);
            continue;
        }
        let end = eventTimestamp(event.end_date, event.end_time, true);
        if (end === null || end < start) {
            const startDay = new Date(start);
            startDay.setHours(24, 0, 0, 0);
            end = startDay.getTime();
        }
        groups[end <= now ? 'past' : 'upcoming'].push(event);
    }
    const byStart = (a, b) => eventTimestamp(a.begin_date, a.begin_time) - eventTimestamp(b.begin_date, b.begin_time);
    groups.upcoming.sort(byStart);
    groups.past.sort((a, b) => byStart(b, a));
    return groups;
}
const ticketName = ticket => [ticket.name, ticket.surname].filter(Boolean).join(' ') || ticket.email || 'Unnamed ticket';
const qs = selector => document.querySelector(selector);

function notice(message, type = 'info') {
    const item = document.createElement('div');
    item.className = `notice ${type}`;
    item.textContent = message;
    notices.append(item);
    window.setTimeout(() => item.remove(), 5000);
}

function reportActionError(error) {
    console.error(error);
    notice(error.message || 'The request could not be completed.', 'error');
}

function xsrfToken() {
    return document.cookie.split('; ').find(row => row.startsWith('_xsrf='))?.split('=').slice(1).join('=') || '';
}

async function api(path, options = {}) {
    const headers = new Headers(options.headers);
    if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
    if (!['GET', 'HEAD'].includes(options.method || 'GET')) headers.set('X-Xsrftoken', xsrfToken());
    const response = await fetch(path, { credentials: 'same-origin', ...options, headers });
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json') ? await response.json() : null;
    if (!response.ok || data?.error) throw new Error(data?.message || `Request failed (${response.status})`);
    return data;
}

function renderNavigation() {
    const user = state.info.user;
    nav.innerHTML = `
        <a href="#/events">Events</a>
        ${hasPermission('admin|all') ? '<a href="#/users">Users</a><a href="#/tickets">All tickets</a><a href="#/import/persons">Import</a>' : ''}
        ${user?._id ? `<a href="#/user/${htmlId(user._id)}/edit">${escapeHtml(user.username)}</a><button class="secondary" data-action="logout">Log out</button>` : '<a href="#/login">Log in</a>'}`;
    qs('[data-action="logout"]')?.addEventListener('click', logout);
}

async function refreshInfo() {
    state.info = (await api('/info')).info || {};
    renderNavigation();
}

function page(title, body, actions = '') {
    app.innerHTML = `<div class="page-heading"><h1>${escapeHtml(title)}</h1><div class="actions">${actions}</div></div>${body}`;
    qs('#main')?.focus();
}

function errorPage(error) {
    page('Something went wrong', `<section class="card error"><p>${escapeHtml(error.message || error)}</p><a class="button" href="#/events">Return to events</a></section>`);
}

function empty(message) { return `<div class="empty">${escapeHtml(message)}</div>`; }

async function showEvents() {
    const data = await api('/events?_summary=true');
    const groups = groupEvents(data.events || []);
    state.events = [...groups.upcoming, ...groups.past, ...groups.undated];
    const eventCard = event => {
        const eventUrl = hasPermission('event|update') ? `#/event/${htmlId(event._id)}/edit` : `#/event/${htmlId(event._id)}/view`;
        const join = !event.no_tickets_for_sale && hasPermission('event:tickets-all|create')
            ? `<a class="button" href="#/event/${htmlId(event._id)}/ticket/new">Register</a>` : '';
        return `<article class="event">
            <div><h2><a href="${eventUrl}">${escapeHtml(event.title || 'Untitled event')}</a></h2>
            ${event.tagline ? `<p>${escapeHtml(event.tagline)}</p>` : ''}
            <p class="metadata">${escapeHtml([formatDate(event.begin_date), event.where].filter(Boolean).join(' · '))}</p>
            <div class="metrics"><span><strong>${event.total_attendees || 0}</strong> attended</span><span><strong>${event.tickets_sold || 0}</strong> registered</span></div></div>
            <div class="actions">${join}${hasPermission('event:tickets-all|read') ? `<a class="button secondary" href="#/event/${htmlId(event._id)}/tickets">Manage tickets</a>` : ''}</div>
        </article>`;
    };
    const cards = Object.entries(groups).filter(([, events]) => events.length).map(([key, events]) => {
        const title = { upcoming: 'Upcoming and current events', past: 'Past events', undated: 'Undated events' }[key];
        return `<section class="event-group"><h2>${title}</h2><div class="event-list">${events.map(eventCard).join('')}</div></section>`;
    }).join('');
    page('Events', `<section class="card"><div class="toolbar"><label>Search events <input id="event-search" type="search" placeholder="Title, place, or summary"></label></div><div id="event-list" class="event-list">${cards || empty('No events yet.')}</div></section>`,
        hasPermission('events|create') || hasPermission('event|create') ? '<a class="button" href="#/event/new">Create event</a>' : '');
    qs('#event-search')?.addEventListener('input', event => {
        const term = event.target.value.toLowerCase();
        document.querySelectorAll('.event').forEach((card, index) => {
            card.hidden = !JSON.stringify(state.events[index]).toLowerCase().includes(term);
        });
        document.querySelectorAll('.event-group').forEach(group => {
            group.hidden = ![...group.querySelectorAll('.event')].some(card => !card.hidden);
        });
    });
}

function eventForm(event, readonly) {
    const value = key => escapeHtml(event[key] || '');
    return `<section class="card">
        ${readonly ? '<p class="hint">You have read-only access to this event.</p>' : ''}
        <form id="event-form"><fieldset ${readonly ? 'disabled' : ''}><div class="grid">
            <label>Title<input name="title" required value="${value('title')}"></label>
            <label>Tagline<input name="tagline" value="${value('tagline')}"></label>
            <label>Location<input name="where" value="${value('where')}"></label>
            <label>Ticket limit<span>Leave blank for unlimited.</span><input name="number_of_tickets" type="number" min="0" value="${value('number_of_tickets')}"></label>
            <label>Starts<input name="begin_date" type="datetime-local" value="${toLocalInput(event.begin_date, event.begin_time)}"></label>
            <label>Ends<input name="end_date" type="datetime-local" value="${toLocalInput(event.end_date, event.end_time)}"></label>
            <label>Sales open<input name="ticket_sales_begin_date" type="datetime-local" value="${toLocalInput(event.ticket_sales_begin_date, event.ticket_sales_begin_time)}"></label>
            <label>Sales close<input name="ticket_sales_end_date" type="datetime-local" value="${toLocalInput(event.ticket_sales_end_date, event.ticket_sales_end_time)}"></label>
        </div>
        <label>Summary<input name="summary" value="${value('summary')}"></label>
        <label>Description<textarea name="description">${value('description')}</textarea></label>
        ${!readonly ? '<div class="actions"><button type="submit">Save event</button></div>' : ''}</fieldset></form></section>`;
}

function toLocalInput(date, time) {
    if (!date) return '';
    const datePart = String(date).slice(0, 10);
    const timePart = time ? String(time).match(/(\d{2}:\d{2})/)?.[1] : '00:00';
    return `${datePart}T${timePart || '00:00'}`;
}

function formValues(form) {
    const data = Object.fromEntries(new FormData(form));
    for (const key of Object.keys(data)) {
        if (data[key] === '') delete data[key];
    }
    return data;
}

function splitDateTime(data, field) {
    if (!data[field]) return;
    const [date, time] = data[field].split('T');
    data[field] = date;
    data[`${field.replace('_date', '')}_time`] = `${time}:00`;
}

async function showEvent(id, editing) {
    const event = await api(`/events/${encodeURIComponent(id)}?_summary=true`);
    state.event = event;
    const canEdit = editing && hasPermission('event|update');
    page(event.title || 'Event', eventForm(event, !canEdit),
        `${hasPermission('event:tickets-all|read') ? `<a class="button secondary" href="#/event/${htmlId(id)}/tickets">Tickets</a>` : ''}${!editing && hasPermission('event:tickets-all|create') ? `<a class="button" href="#/event/${htmlId(id)}/ticket/new">Register</a>` : ''}${canEdit && hasPermission('event|delete') ? `<button class="danger" id="delete-event">Delete event</button>` : ''}`);
    qs('#event-form')?.addEventListener('submit', async submit => {
        submit.preventDefault();
        try {
            const data = formValues(submit.currentTarget);
            ['begin_date', 'end_date', 'ticket_sales_begin_date', 'ticket_sales_end_date'].forEach(field => splitDateTime(data, field));
            await api(`/events/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(data) });
            notice('Event saved.', 'success');
            location.hash = `#/event/${encodeURIComponent(id)}/edit`;
        } catch (error) {
            reportActionError(error);
        }
    });
    qs('#delete-event')?.addEventListener('click', async () => {
        if (!window.confirm('Permanently delete this event and all of its tickets?')) return;
        await api(`/events/${encodeURIComponent(id)}`, { method: 'DELETE' });
        notice('Event deleted.', 'success');
        location.hash = '#/events';
    });
}

async function showNewEvent() {
    if (!hasPermission('event|create') && !hasPermission('events|create')) throw new Error('You do not have permission to create events.');
    page('Create event', eventForm({}, false));
    qs('#event-form').addEventListener('submit', async submit => {
        submit.preventDefault();
        try {
            const data = formValues(submit.currentTarget);
            ['begin_date', 'end_date', 'ticket_sales_begin_date', 'ticket_sales_end_date'].forEach(field => splitDateTime(data, field));
            data.formSchema = defaultFormSchema;
            const event = await api('/events', { method: 'POST', body: JSON.stringify(data) });
            notice('Event created.', 'success');
            location.hash = `#/event/${encodeURIComponent(event._id)}/edit`;
        } catch (error) {
            reportActionError(error);
        }
    });
}

function schemaFields(schema) {
    return (schema?.formlyFieldsModel || []).flatMap(row => row.fieldGroup || []).map(field => ({
        key: (field.templateOptions?.label || field.key).toLowerCase(),
        label: field.templateOptions?.label || field.key,
        type: field.templateOptions?.type || field.type || 'text',
        required: Boolean(field.templateOptions?.required),
        placeholder: field.templateOptions?.placeholder || '',
        options: field.templateOptions?.options || []
    }));
}

function ticketForm(event, ticket = {}) {
    const fields = schemaFields(event.formSchema);
    if (!fields.length) fields.push(...['Name', 'Surname', 'Email', 'Job title', 'Company'].map(label => ({ key: label.toLowerCase(), label, type: 'text', required: false, options: [] })));
    const controls = fields.map(field => {
        const value = escapeHtml(ticket[field.key] ?? '');
        const required = field.required ? 'required' : '';
        if (field.type === 'checkbox' || field.type === 'boolean') return `<label><input class="check" type="checkbox" name="${escapeHtml(field.key)}" ${ticket[field.key] ? 'checked' : ''}> ${escapeHtml(field.label)}</label>`;
        if (field.type === 'select' && field.options.length) return `<label>${escapeHtml(field.label)}<select name="${escapeHtml(field.key)}" ${required}>${field.options.map(option => `<option value="${escapeHtml(option.value ?? option.name ?? option)}" ${(option.value ?? option.name ?? option) == ticket[field.key] ? 'selected' : ''}>${escapeHtml(option.name ?? option.label ?? option.value ?? option)}</option>`).join('')}</select></label>`;
        const inputType = /email/i.test(field.label) ? 'email' : field.type === 'textarea' ? null : 'text';
        return `<label>${escapeHtml(field.label)}${inputType ? `<input type="${inputType}" name="${escapeHtml(field.key)}" value="${value}" placeholder="${escapeHtml(field.placeholder)}" ${required}>` : `<textarea name="${escapeHtml(field.key)}" ${required}>${value}</textarea>`}</label>`;
    }).join('');
    return `<section class="card"><form id="ticket-form"><div class="grid">${controls}</div>
        ${ticket._id ? `<label class="warning"><input class="check" type="checkbox" name="cancelled" ${ticket.cancelled ? 'checked' : ''}> Cancel this registration</label>` : ''}
        <div class="actions"><button type="submit">${ticket._id ? 'Save ticket' : 'Register'}</button><a class="button secondary" href="#/events">Cancel</a></div></form></section>`;
}

async function showTicketForm(eventId, ticketId) {
    const event = await api(`/events/${encodeURIComponent(eventId)}`);
    const ticket = ticketId ? (await api(`/events/${encodeURIComponent(eventId)}/tickets/${encodeURIComponent(ticketId)}`)).ticket : {};
    const guestNote = !ticketId && !state.info.user?.isRegistered
        ? '<p class="warning">To manage this registration later, <a href="#/login">create an account or log in</a> before registering. Guest registrations can only be managed by authorized staff.</p>' : '';
    page(ticketId ? `Edit ticket · ${event.title}` : `Register · ${event.title}`, guestNote + ticketForm(event, ticket),
        `<a class="button secondary" href="#/event/${htmlId(eventId)}/view">View event</a>${hasPermission('event:tickets-all|read') ? `<a class="button secondary" href="#/event/${htmlId(eventId)}/tickets">Back to tickets</a>` : ''}`);
    qs('#ticket-form').addEventListener('submit', async submit => {
        submit.preventDefault();
        const data = formValues(submit.currentTarget);
        schemaFields(event.formSchema).filter(field => field.type === 'checkbox' || field.type === 'boolean').forEach(field => { data[field.key] = submit.currentTarget.elements[field.key].checked; });
        if (ticketId) data.cancelled = submit.currentTarget.elements.cancelled.checked;
        const url = ticketId ? `/events/${encodeURIComponent(eventId)}/tickets/${encodeURIComponent(ticketId)}` : `/events/${encodeURIComponent(eventId)}/tickets`;
        const saved = await api(url, { method: ticketId ? 'PUT' : 'POST', body: JSON.stringify(data) });
        notice(ticketId ? 'Ticket saved.' : 'Registration complete.', 'success');
        if (!ticketId && !state.info.user?.isRegistered) {
            page('Registration complete', '<section class="card"><p>Your registration was saved. Contact authorized event staff if you need to change or cancel it.</p></section>',
                `<a class="button secondary" href="#/event/${htmlId(eventId)}/view">View event</a>`);
            return;
        }
        location.hash = `#/event/${encodeURIComponent(eventId)}/ticket/${encodeURIComponent(ticketId || saved.ticket?._id || saved._id)}/edit`;
    });
}

function filteredTickets(tickets, term, cancelled) {
    return tickets.filter(ticket => (cancelled || !ticket.cancelled) && JSON.stringify(ticket).toLowerCase().includes(term.toLowerCase()));
}

async function showTickets(id) {
    const event = await api(`/events/${encodeURIComponent(id)}`);
    state.event = event;
    const renderRows = () => {
        const visible = filteredTickets(event.tickets || [], qs('#ticket-search').value, qs('#show-cancelled').checked);
        qs('#ticket-count').textContent = `${visible.length} shown · ${(event.tickets || []).filter(ticket => ticket.attended && !ticket.cancelled).length} attended`;
        qs('#ticket-rows').innerHTML = visible.map(ticket => `<tr class="${ticket.cancelled ? 'cancelled' : ''}">
            <td>${escapeHtml(ticket.seq_hex || '')}</td><td><a href="#/event/${htmlId(id)}/ticket/${htmlId(ticket._id)}/edit">${escapeHtml(ticketName(ticket))}</a><div class="metadata">${escapeHtml(ticket.email || '')}</div></td>
            <td class="hide-small">${escapeHtml(ticket.company || '')}</td><td><input class="check" type="checkbox" data-attendance="${escapeHtml(ticket._id)}" ${ticket.attended ? 'checked' : ''} aria-label="Mark ${escapeHtml(ticketName(ticket))} as attended"></td>
            <td><button class="secondary" data-delete-ticket="${escapeHtml(ticket._id)}">Delete</button></td></tr>`).join('') || `<tr><td colspan="5">${empty('No tickets match your search.')}</td></tr>`;
        document.querySelectorAll('[data-attendance]').forEach(input => input.addEventListener('change', () => updateTicket(id, input.dataset.attendance, { attended: input.checked })));
        document.querySelectorAll('[data-delete-ticket]').forEach(button => button.addEventListener('click', () => deleteTicket(id, button.dataset.deleteTicket)));
    };
    page(`Tickets · ${event.title}`, `<section class="card"><div class="toolbar"><div class="actions"><label>Search tickets<input id="ticket-search" type="search" placeholder="Name, email, or field"></label><label><input id="show-cancelled" type="checkbox"> Show cancelled</label></div><span id="ticket-count" class="status"></span></div><div class="table-wrap"><table><thead><tr><th>#</th><th>Person</th><th class="hide-small">Company</th><th>Attended</th><th>Actions</th></tr></thead><tbody id="ticket-rows"></tbody></table></div></section>`,
        `<a class="button" href="#/event/${htmlId(id)}/ticket/new">Add ticket</a><a class="button secondary" href="#/event/${htmlId(id)}/edit">Edit event</a>`);
    qs('#ticket-search').addEventListener('input', renderRows);
    qs('#show-cancelled').addEventListener('change', renderRows);
    renderRows();
    connectUpdates(id, renderRows);
}

async function updateTicket(eventId, ticketId, data) {
    await api(`/events/${encodeURIComponent(eventId)}/tickets/${encodeURIComponent(ticketId)}`, { method: 'PUT', body: JSON.stringify(data) });
    notice('Ticket updated.', 'success');
}

async function deleteTicket(eventId, ticketId) {
    if (!window.confirm('Permanently delete this ticket?')) return;
    await api(`/events/${encodeURIComponent(eventId)}/tickets/${encodeURIComponent(ticketId)}`, { method: 'DELETE' });
    notice('Ticket deleted.', 'success');
    location.hash = `#/event/${encodeURIComponent(eventId)}/tickets`;
}

function connectUpdates(id, rerender) {
    state.socket?.close();
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${location.host}/ws/event/${encodeURIComponent(id)}/tickets/updates?uuid=${crypto.randomUUID()}`;
    state.socket = new WebSocket(url);
    state.socket.addEventListener('message', event => {
        const update = JSON.parse(event.data);
        const tickets = state.event.tickets || (state.event.tickets = []);
        const index = tickets.findIndex(ticket => ticket._id === (update._id || update.ticket?._id));
        if (update.action === 'delete' && index >= 0) tickets.splice(index, 1);
        else if (update.action === 'update' && index >= 0) tickets[index] = update.ticket;
        else if (update.action === 'add' && index < 0) tickets.push(update.ticket);
        rerender();
    });
}

async function showLogin() {
    page('Log in', `<div class="grid"><section class="card"><h2>Log in</h2><form id="login-form"><label>Username or email<input name="username" autocomplete="username" required></label><label>Password<input name="password" type="password" autocomplete="current-password" required></label><div class="actions"><button>Log in</button></div></form></section><section class="card"><h2>Create account</h2><form id="register-form"><label>Username<input name="username" autocomplete="username" required></label><label>Email<input name="email" type="email" autocomplete="email"></label><label>Password<input name="password" type="password" autocomplete="new-password" required minlength="12"></label><div class="actions"><button>Create account</button></div></form></section></div>`);
    qs('#login-form').addEventListener('submit', async event => { event.preventDefault(); await api('/login', { method: 'POST', body: JSON.stringify(formValues(event.currentTarget)) }); await refreshInfo(); location.hash = '#/events'; });
    qs('#register-form').addEventListener('submit', async event => { event.preventDefault(); const user = formValues(event.currentTarget); await api('/users', { method: 'POST', body: JSON.stringify(user) }); await api('/login', { method: 'POST', body: JSON.stringify(user) }); await refreshInfo(); location.hash = '#/events'; });
}

async function logout() {
    await api('/logout');
    await refreshInfo();
    location.hash = '#/login';
}

async function showUsers() {
    if (!hasPermission('users|read')) throw new Error('You do not have permission to view users.');
    const users = (await api('/users')).users || [];
    page('Users', `<section class="card"><label>Search users<input id="user-search" type="search"></label><div class="table-wrap"><table><thead><tr><th>Username</th><th>Email</th><th>Actions</th></tr></thead><tbody id="user-rows"></tbody></table></div></section>`, '<a class="button" href="#/login">Add user</a>');
    const draw = () => {
        const term = qs('#user-search').value.toLowerCase();
        qs('#user-rows').innerHTML = users.filter(user => JSON.stringify(user).toLowerCase().includes(term)).map(user => `<tr><td><a href="#/user/${htmlId(user._id)}/edit">${escapeHtml(user.username)}</a></td><td>${escapeHtml(user.email || '')}</td><td>${hasPermission('user|delete') ? `<button class="danger" data-delete-user="${escapeHtml(user._id)}">Delete</button>` : ''}</td></tr>`).join('');
        document.querySelectorAll('[data-delete-user]').forEach(button => button.addEventListener('click', async () => { if (confirm('Delete this user?')) { await api(`/users/${encodeURIComponent(button.dataset.deleteUser)}`, { method: 'DELETE' }); location.hash = '#/users'; }}));
    };
    qs('#user-search').addEventListener('input', draw); draw();
}

async function showAllTickets() {
    if (!hasPermission('admin|all')) throw new Error('You do not have permission to view all tickets.');
    const tickets = (await api('/tickets')).tickets || [];
    page('All tickets', `<section class="card"><label>Search tickets<input id="all-ticket-search" type="search" placeholder="Name, email, or event"></label><div class="table-wrap"><table><thead><tr><th>Person</th><th>Event</th><th>Email</th><th>Attended</th></tr></thead><tbody id="all-ticket-rows"></tbody></table></div></section>`);
    const draw = () => {
        const term = qs('#all-ticket-search').value.toLowerCase();
        qs('#all-ticket-rows').innerHTML = tickets.filter(ticket => JSON.stringify(ticket).toLowerCase().includes(term)).map(ticket => `<tr><td><a href="#/event/${htmlId(ticket.event_id)}/ticket/${htmlId(ticket._id)}/edit">${escapeHtml(ticketName(ticket))}</a></td><td><a href="#/event/${htmlId(ticket.event_id)}/view">${escapeHtml(ticket.event_title || 'View event')}</a></td><td>${escapeHtml(ticket.email || '')}</td><td>${ticket.attended ? '<span class="status success">Yes</span>' : '<span class="status">No</span>'}</td></tr>`).join('') || `<tr><td colspan="4">${empty('No tickets match your search.')}</td></tr>`;
    };
    qs('#all-ticket-search').addEventListener('input', draw); draw();
}

async function showUser(id) {
    const user = await api(`/users/${encodeURIComponent(id)}`);
    page(`Account · ${user.username}`, `<section class="card"><form id="user-form"><div class="grid"><label>Email<input name="email" type="email" value="${escapeHtml(user.email || '')}"></label><label>Current password<input name="old_password" type="password" autocomplete="current-password"></label><label>New password<input name="new_password" type="password" autocomplete="new-password" minlength="12"></label>${hasPermission('admin|all') ? `<label><input class="check" name="isAdmin" type="checkbox" ${hasPermissionForUser(user, 'admin|all') ? 'checked' : ''}> Administrator</label>` : ''}</div><div class="actions"><button>Save account</button></div></form></section>`);
    qs('#user-form').addEventListener('submit', async event => { event.preventDefault(); const data = formValues(event.currentTarget); if (event.currentTarget.elements.isAdmin) data.isAdmin = event.currentTarget.elements.isAdmin.checked; await api(`/users/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(data) }); notice('Account saved.', 'success'); });
}
const hasPermissionForUser = (user, permission) => (user.permissions || []).includes(permission);

async function showImport() {
    if (!hasPermission('admin|all')) throw new Error('You do not have permission to import tickets.');
    const events = (await api('/events?_summary=true')).events || [];
    const options = events.map(event => `<option value="${escapeHtml(event._id)}">${escapeHtml(event.title)}</option>`).join('');
    page('Import tickets', `<div class="grid"><section class="card"><h2>Eventbrite API</h2><form id="eventbrite-form"><label>OAuth token<input name="oauthToken" type="password" required></label><label>Eventbrite event ID<input name="eventID" required></label><label><input class="check" name="create" type="checkbox" checked> Create a new event</label><label>Existing event<select name="targetEvent"><option value="">Select an event</option>${options}</select></label><button>Import from Eventbrite</button></form></section><section class="card"><h2>Eventbrite CSV</h2><form id="csv-form"><label>CSV file<input name="file" type="file" accept=".csv,text/csv" required></label><label>Event<select name="targetEvent" required><option value="">Select an event</option>${options}</select></label><label><input class="check" name="deduplicate" type="checkbox"> Deduplicate entries</label><button>Upload CSV</button></form></section></div>`);
    qs('#eventbrite-form').addEventListener('submit', async event => { event.preventDefault(); const data = formValues(event.currentTarget); data.create = event.currentTarget.elements.create.checked; const result = await api('/ebapi', { method: 'POST', body: JSON.stringify(data) }); notice(`Import complete: ${result.new_in_event || 0} tickets added.`, 'success'); });
    qs('#csv-form').addEventListener('submit', async event => { event.preventDefault(); const form = new FormData(event.currentTarget); form.set('deduplicate', event.currentTarget.elements.deduplicate.checked); const result = await api('/ebcsvpersons', { method: 'POST', body: form }); notice(`Import complete: ${result.new_in_event || 0} tickets added.`, 'success'); });
}

async function render() {
    state.socket?.close(); state.socket = null;
    try {
        const parts = route().split('/').slice(1);
        if (parts[0] === 'events') return showEvents();
        if (parts[0] === 'event' && parts[1] === 'new') return showNewEvent();
        if (parts[0] === 'event' && parts[2] === 'tickets') return showTickets(routeId(parts[1]));
        if (parts[0] === 'event' && parts[2] === 'ticket') return showTicketForm(routeId(parts[1]), parts[3] === 'new' ? null : routeId(parts[3]));
        if (parts[0] === 'event') return showEvent(routeId(parts[1]), parts[2] === 'edit');
        if (parts[0] === 'login') return showLogin();
        if (parts[0] === 'users') return showUsers();
        if (parts[0] === 'tickets') return showAllTickets();
        if (parts[0] === 'user') return showUser(routeId(parts[1]));
        if (parts[0] === 'import') return showImport();
        location.hash = '#/events';
    } catch (error) {
        if (error.message.includes('authentication required')) location.hash = '#/login';
        else errorPage(error);
    }
}

window.addEventListener('hashchange', render);
await refreshInfo();
render();
