const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000/api`;

const eventList = document.getElementById('event-list');
const registrationForm = document.getElementById('registration-form');
const eventSelect = registrationForm?.elements?.eventId ?? null;
const modalRegisterButton = document.getElementById('event-modal-register');
const upcomingCount = document.getElementById('upcoming-count');
const registeredCount = document.getElementById('registered-count');
const slotsLeftCount = document.getElementById('slots-left-count');
const eventModal = document.getElementById('event-modal');
const eventModalTitle = document.getElementById('event-modal-title');
const eventModalMeta = document.getElementById('event-modal-meta');
const eventModalDescription = document.getElementById('event-modal-description');
const eventModalLocation = document.getElementById('event-modal-location');
const eventModalDate = document.getElementById('event-modal-date');
const eventModalSlots = document.getElementById('event-modal-slots');
const eventModalClose = document.getElementById('event-modal-close');
const registerModal = document.getElementById('register-modal');
const registerModalTitle = document.getElementById('register-modal-title');
const registerModalDescription = document.getElementById('register-modal-description');
const registerModalClose = document.getElementById('register-modal-close');
const registerModalCancel = document.getElementById('register-modal-cancel');
const registerModalConfirm = document.getElementById('register-modal-confirm');

let currentEvents = [];
let currentModalEventId = null;
let pendingResumeUrl = '';
let currentRegisteredEventIds = [];

function normalizeAccountValue(value) {
  return String(value || '').trim().toLowerCase();
}

function getAccountRegistrationKey(studentNumber = localStorage.getItem('ueventStudentNumber'), studentEmail = localStorage.getItem('ueventStudentEmail')) {
  const numberPart = normalizeAccountValue(studentNumber);
  const emailPart = normalizeAccountValue(studentEmail);

  if (!numberPart && !emailPart) {
    return 'ueventRegisteredEventIds:guest';
  }

  return `ueventRegisteredEventIds:${numberPart}:${emailPart}`;
}

function getLegacyRegisteredEventIds() {
  try {
    return JSON.parse(localStorage.getItem('ueventRegisteredEventIds') || '[]').map(String);
  } catch (_) {
    return [];
  }
}

function getStoredEventIdsForCurrentAccount() {
  const accountKey = getAccountRegistrationKey();

  try {
    const current = JSON.parse(localStorage.getItem(accountKey) || '[]').map(String);
    if (current.length > 0) {
      return current;
    }

    const legacy = getLegacyRegisteredEventIds();
    if (legacy.length > 0) {
      localStorage.setItem(accountKey, JSON.stringify(legacy));
      return legacy;
    }

    return [];
  } catch (_) {
    return [];
  }
}

async function loadRegisteredEventIds() {
  try {
    const response = await fetch(`${API_BASE_URL}/registrations/`, {
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error(`Status ${response.status}`);
    }

    const registrations = await response.json();
    currentRegisteredEventIds = Array.isArray(registrations)
      ? registrations.map((registration) => String(registration.event))
      : [];

    const accountKey = getAccountRegistrationKey();
    localStorage.setItem(accountKey, JSON.stringify(currentRegisteredEventIds));
    localStorage.setItem('ueventRegisteredEventIds', JSON.stringify(currentRegisteredEventIds));

    return currentRegisteredEventIds;
  } catch (_) {
    currentRegisteredEventIds = getStoredEventIdsForCurrentAccount();
    return currentRegisteredEventIds;
  }
}

function getQueryParam(name) {
  const url = new URL(window.location.href);
  return url.searchParams.get(name);
}

function hydrateUserFromUrl() {
  const studentNumber = getQueryParam('student_number');
  const studentEmail = getQueryParam('student_email');

  if (studentNumber) {
    localStorage.setItem('ueventStudentNumber', studentNumber);
  }

  if (studentEmail) {
    localStorage.setItem('ueventStudentEmail', studentEmail);
  }

  const registered = getQueryParam('registered');
  if (registered && studentNumber && studentEmail) {
    const accountKey = getAccountRegistrationKey(studentNumber, studentEmail);
    const stored = JSON.parse(localStorage.getItem(accountKey) || '[]').map(String);
    if (!stored.includes(String(registered))) {
      stored.push(String(registered));
      localStorage.setItem(accountKey, JSON.stringify(stored));
    }
    localStorage.setItem('ueventRegisteredEventIds', JSON.stringify(stored));
  }
}

function storeRegisteredEventFromUrl() {
  const registeredId = getQueryParam('registered');
  if (!registeredId) {
    return;
  }

  const accountKey = getAccountRegistrationKey();
  const stored = JSON.parse(localStorage.getItem(accountKey) || '[]');
  const normalized = String(registeredId);

  if (!stored.includes(normalized)) {
    stored.push(normalized);
    localStorage.setItem(accountKey, JSON.stringify(stored));
  }

  localStorage.setItem('ueventRegisteredEventIds', JSON.stringify(stored));
  localStorage.setItem('ueventLastRegisteredEventId', normalized);
  localStorage.setItem('ueventLastRegisteredAt', new Date().toISOString());

  const bannerId = 'registration-banner';
  let banner = document.getElementById(bannerId);
  if (!banner) {
    banner = document.createElement('div');
    banner.id = bannerId;
    banner.className = 'registration-banner';
    banner.innerHTML = `
      <span class="banner-icon" aria-hidden="true">✓</span>
      <div>
        <strong>Registration complete.</strong>
        <p>You can open your profile to see the registered event.</p>
      </div>
    `;
    const hero = document.querySelector('.hero');
    if (hero && hero.parentNode) {
      hero.parentNode.insertBefore(banner, hero.nextSibling);
    }
  }

  const cleanUrl = new URL(window.location.href);
  cleanUrl.searchParams.delete('registered');
  window.history.replaceState({}, '', cleanUrl.toString());
}

function isEventRegistered(eventId) {
  return currentRegisteredEventIds.includes(String(eventId));
}

if (registrationForm?.elements.studentId) {
  registrationForm.elements.studentId.addEventListener('input', (event) => {
    event.target.value = event.target.value.replace(/\D/g, '');
  });
}

function updateEventSelect(events) {
  if (!eventSelect) {
    return;
  }

  const options = ['<option value="">Select an event</option>']
    .concat(
      events.map(
        (event) => `<option value="${event.id}">${event.title}</option>`
      )
    )
    .join('');

  eventSelect.innerHTML = options;
}

function updateHeroStats(events) {
  if (upcomingCount) {
    upcomingCount.textContent = events.length;
  }

  const totalRegistered = events.reduce((sum, event) => sum + Number(event.registered_count || 0), 0);
  const totalSlotsLeft = events.reduce((sum, event) => sum + Number(event.remaining_slots || 0), 0);

  if (registeredCount) {
    registeredCount.textContent = totalRegistered;
  }

  if (slotsLeftCount) {
    slotsLeftCount.textContent = totalSlotsLeft;
  }
}

function formatEventDate(dateValue) {
  if (!dateValue) {
    return 'Date not set';
  }

  const parsedDate = new Date(dateValue);

  if (Number.isNaN(parsedDate.getTime())) {
    return dateValue;
  }

  return parsedDate.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function getIconSvg(name) {
  const icons = {
    location: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s6-5.5 6-12a6 6 0 0 0-12 0c0 6.5 6 12 6 12zm0-9a3 3 0 1 1 0-6 3 3 0 0 1 0 6z"/></svg>',
    calendar: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 4h-1V2h-2v2H8V2H6v2H5c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-12 6h10v6H7v-6z"/></svg>',
    slots: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a4 4 0 0 1 4 4c0 1.66-1.01 3.08-2.45 3.72C16.86 10.36 19 12.76 19 16h-2c0-2.76-2.24-5-5-5s-5 2.24-5 5H5c0-3.24 2.14-5.64 5.45-6.28A4 4 0 0 1 12 2zm0 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"/></svg>',
    info: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 17h2v-6h-2v6zm0-8h2V7h-2v2zm1 13a10 10 0 1 1 0-20 10 10 0 0 1 0 20z"/></svg>',
  };

  return icons[name] || icons.info;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function renderDetailRow(iconName, label, value) {
  return `
    <div class="modal-info-row">
      <span class="icon-pill" aria-hidden="true">${getIconSvg(iconName)}</span>
      <div>
        <span class="detail-label">${label}</span>
        <strong>${escapeHtml(value)}</strong>
      </div>
    </div>
  `;
}

function openEventModal(event) {
  if (!eventModal) {
    return;
  }

  if (eventModalTitle) {
    eventModalTitle.textContent = event.title || 'Event details';
  }

  if (eventModalMeta) {
    eventModalMeta.innerHTML = `
      <span class="meta-chip">
        ${getIconSvg('location')}
        ${escapeHtml(event.location || 'No location provided')}
      </span>
      <span class="meta-chip">
        ${getIconSvg('calendar')}
        ${escapeHtml(formatEventDate(event.date))}
      </span>
    `;
  }

  if (eventModalDescription) {
    const descriptionText = event.description?.trim()
      ? event.description.trim()
      : 'This event does not have a description yet.';

    eventModalDescription.innerHTML = `
      <div class="description-heading">
        <span class="icon-pill icon-pill-soft" aria-hidden="true">${getIconSvg('info')}</span>
        <div>
          <span class="detail-label">About this event</span>
          <strong>${escapeHtml(event.title || 'Event')}</strong>
        </div>
      </div>
      <p>${escapeHtml(descriptionText)}</p>
    `;
  }

  if (eventModalLocation) {
    eventModalLocation.textContent = event.location || 'No location provided';
  }

  if (eventModalDate) {
    eventModalDate.textContent = formatEventDate(event.date);
  }

  if (eventModalSlots) {
    eventModalSlots.textContent = `${event.remaining_slots ?? 0} slots left`;
  }

  currentModalEventId = event.id;

  if (modalRegisterButton) {
    const alreadyRegistered = isEventRegistered(event.id);
    modalRegisterButton.textContent = alreadyRegistered ? 'Already Registered' : 'Register';
    modalRegisterButton.disabled = alreadyRegistered;
    modalRegisterButton.classList.toggle('is-registered', alreadyRegistered);
  }

  const modalInfo = document.querySelector('.modal-info');
  if (modalInfo) {
    modalInfo.innerHTML = [
      renderDetailRow('location', 'Location', event.location || 'No location provided'),
      renderDetailRow('calendar', 'Date', formatEventDate(event.date)),
      renderDetailRow('slots', 'Slots', `${event.remaining_slots ?? 0} slots left`),
    ].join('');
  }

  eventModal.setAttribute('aria-hidden', 'false');
  eventModal.classList.add('is-open');
}

function openRegisterModal(event) {
  if (!registerModal || !registerModalDescription || !registerModalTitle) {
    return;
  }

  pendingResumeUrl = `${API_BASE_URL}/registrations/resume/?event_id=${encodeURIComponent(event.id)}&redirect=${encodeURIComponent(window.location.href + '?registered=' + encodeURIComponent(event.id))}`;

  registerModalTitle.textContent = `Register for ${event.title || 'this event'}`;
  registerModalDescription.innerHTML = `
    <p>You are about to register for <strong>${escapeHtml(event.title || 'this event')}</strong>.</p>
    <div class="modal-info-row register-summary-row">
      <span class="icon-pill" aria-hidden="true">${getIconSvg('calendar')}</span>
      <div>
        <span class="detail-label">Date</span>
        <strong>${escapeHtml(formatEventDate(event.date))}</strong>
      </div>
    </div>
    <div class="modal-info-row register-summary-row">
      <span class="icon-pill" aria-hidden="true">${getIconSvg('location')}</span>
      <div>
        <span class="detail-label">Location</span>
        <strong>${escapeHtml(event.location || 'No location provided')}</strong>
      </div>
    </div>
    <p class="register-note">If you are not signed in, you will be asked to log in first. After login, registration completes automatically.</p>
  `;

  const alreadyRegistered = isEventRegistered(event.id);
  if (registerModalConfirm) {
    registerModalConfirm.textContent = alreadyRegistered ? 'Registered' : 'Continue';
    registerModalConfirm.disabled = alreadyRegistered;
    registerModalConfirm.classList.toggle('is-registered', alreadyRegistered);
  }

  registerModal.setAttribute('aria-hidden', 'false');
  registerModal.classList.add('is-open');
}

function closeRegisterModal() {
  if (!registerModal) {
    return;
  }

  registerModal.setAttribute('aria-hidden', 'true');
  registerModal.classList.remove('is-open');
}

function closeEventModal() {
  if (!eventModal) {
    return;
  }

  eventModal.setAttribute('aria-hidden', 'true');
  eventModal.classList.remove('is-open');
}

async function loadEvents() {
  if (!eventList) {
    return;
  }

  eventList.innerHTML = '<p>Loading events...</p>';

  try {
    await loadRegisteredEventIds();
    const response = await fetch(`${API_BASE_URL}/events/`);

    if (!response.ok) {
      let bodyText = '';
      try {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          const json = await response.json();
          bodyText = JSON.stringify(json);
        } else {
          bodyText = await response.text();
        }
      } catch (err) {
        bodyText = '<unable to read response body>';
      }

      eventList.innerHTML = `
        <p>Unable to load events from the backend.</p>
        <p>Status: ${response.status} ${escapeHtml(response.statusText || '')}</p>
        <pre class="debug-body">${escapeHtml(bodyText)}</pre>
      `;
      return;
    }

    const events = await response.json();
    currentEvents = Array.isArray(events) ? events : [];

    if (!Array.isArray(events) || events.length === 0) {
      eventList.innerHTML = '<p>No events available yet.</p>';
      updateEventSelect([]);
      updateHeroStats([]);
      return;
    }

    updateEventSelect(events);
    updateHeroStats(events);

    eventList.innerHTML = events
      .map(
        (event) => `
          <button class="event-item event-button ${isEventRegistered(event.id) ? 'is-registered' : ''}" type="button" data-event-id="${event.id}">
            <div>
              <div class="event-title-row">
                <h4>${event.title}</h4>
                <span class="event-chevron" aria-hidden="true">
                  <svg viewBox="0 0 24 24"><path d="M9.29 6.71 13.59 11H4v2h9.59l-4.3 4.29L10.7 18.7 17.4 12 10.7 5.3z"/></svg>
                </span>
              </div>
              <div class="event-meta">
                <span>${formatEventDate(event.date)}</span>
                <span class="meta-separator" aria-hidden="true">•</span>
                <span>${event.remaining_slots} slots left</span>
                <span class="meta-separator" aria-hidden="true">•</span>
                <span>${event.location || 'Location TBA'}</span>
              </div>
            </div>
            <span class="pill ${isEventRegistered(event.id) ? 'is-registered' : ''}">${isEventRegistered(event.id) ? 'Registered' : (event.is_active ? 'Open' : 'Closed')}</span>
          </button>
        `
      )
      .join('');

    eventList.querySelectorAll('[data-event-id]').forEach((button) => {
      button.addEventListener('click', () => {
        const selectedEvent = currentEvents.find((entry) => String(entry.id) === button.dataset.eventId);

        if (selectedEvent) {
          openEventModal(selectedEvent);
        }
      });
    });
  } catch (error) {
    console.error('Error fetching /events/', error);
    const message = (error && error.message) ? error.message : String(error);
    eventList.innerHTML = `
      <p>Unable to load events from the backend.</p>
      <p>Error: ${escapeHtml(message)}</p>
    `;
  }
}

if (modalRegisterButton) {
  modalRegisterButton.addEventListener('click', () => {
    if (!currentModalEventId) return;

    const selectedEvent = currentEvents.find((entry) => String(entry.id) === String(currentModalEventId));
    if (!selectedEvent) return;

    openRegisterModal(selectedEvent);
  });
}

if (registerModalConfirm) {
  registerModalConfirm.addEventListener('click', () => {
    if (pendingResumeUrl) {
      window.location.href = pendingResumeUrl;
    }
  });
}

if (registerModalClose) {
  registerModalClose.addEventListener('click', closeRegisterModal);
}

if (registerModalCancel) {
  registerModalCancel.addEventListener('click', closeRegisterModal);
}

if (registerModal) {
  registerModal.addEventListener('click', (event) => {
    if (event.target === registerModal) {
      closeRegisterModal();
    }
  });
}

if (eventModalClose) {
  eventModalClose.addEventListener('click', closeEventModal);
}

if (eventModal) {
  eventModal.addEventListener('click', (event) => {
    if (event.target === eventModal) {
      closeEventModal();
    }
  });
}

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    closeEventModal();
    closeRegisterModal();
  }
});

// ==========================================
// AUTHENTICATION GUARD
// ==========================================
hydrateUserFromUrl();

const currentStudentNum = localStorage.getItem('ueventStudentNumber');
const currentStudentEmail = localStorage.getItem('ueventStudentEmail');

if (!currentStudentNum || !currentStudentEmail) {
  window.location.href = 'login.html';
} else {
  storeRegisteredEventFromUrl();
  loadEvents();
}