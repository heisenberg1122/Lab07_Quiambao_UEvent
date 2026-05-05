const API_BASE_URL = 'http://127.0.0.1:8000/api';

const eventList = document.getElementById('event-list');
const registrationForm = document.getElementById('registration-form');
const eventSelect = registrationForm?.elements.eventId;
const formNote = document.querySelector('.form-note');
const upcomingCount = document.getElementById('upcoming-count');
const registeredCount = document.getElementById('registered-count');
const slotsLeftCount = document.getElementById('slots-left-count');

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

async function loadEvents() {
  if (!eventList) {
    return;
  }

  eventList.innerHTML = '<p>Loading events...</p>';

  try {
    const response = await fetch(`${API_BASE_URL}/events/`);
    const events = await response.json();

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
          <article class="event-item">
            <div>
              <h4>${event.title}</h4>
              <div class="event-meta">
                <span>${event.date}</span>
                <span>${event.remaining_slots} slots left</span>
              </div>
            </div>
            <span class="pill">${event.is_active ? 'Open' : 'Closed'}</span>
          </article>
        `
      )
      .join('');
  } catch (error) {
    eventList.innerHTML = '<p>Unable to load events from the backend.</p>';
  }
}

if (registrationForm) {
  registrationForm.addEventListener('submit', (event) => {
    event.preventDefault();
    submitRegistration();
  });
}

async function submitRegistration() {
  const submitButton = registrationForm.querySelector('button[type="submit"]');
  const studentId = registrationForm.elements.studentId.value.trim();
  const eventId = registrationForm.elements.eventId.value;

  if (!studentId || !eventId) {
    formNote.textContent = 'Please enter a student number and choose an event.';
    return;
  }

  submitButton.disabled = true;
  formNote.textContent = 'Submitting registration...';

  try {
    const response = await fetch(`${API_BASE_URL}/registrations/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: studentId,
        event_id: Number(eventId),
      }),
    });

    const result = await response.json();

    if (result.status === 'success') {
      formNote.textContent = result.message;
      registrationForm.reset();
      await loadEvents();
      return;
    }

    formNote.textContent = result.message || 'Registration failed.';
  } catch (error) {
    formNote.textContent = 'Could not reach the backend API.';
  } finally {
    submitButton.disabled = false;
  }
}

loadEvents();
