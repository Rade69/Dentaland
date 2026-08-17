const monthNames = [
  "Januar", "Februar", "Mart", "April", "Maj", "Juni",
  "Juli", "Avgust", "Septembar", "Oktobar", "Novembar", "Decembar",
];
const dayNames = [
  "nedjelja", "ponedjeljak", "utorak", "srijeda", "četvrtak", "petak", "subota",
];

const today = new Date();
today.setHours(0, 0, 0, 0);

let displayedMonth = new Date(today.getFullYear(), today.getMonth(), 1);
let selectedDate = null;
let currentStep = 1;

const grid = document.querySelector("#calendar-grid");
const monthLabel = document.querySelector("#month-label");
const previousMonthButton = document.querySelector("#previous-month");
const nextMonthButton = document.querySelector("#next-month");
const form = document.querySelector("#booking-form");
const continueButton = document.querySelector("#continue-button");
const selectedDateLabel = document.querySelector("#selected-date");
const fullNameInput = document.querySelector("#full-name");
const phoneInput = document.querySelector("#phone");
const emailInput = document.querySelector("#email");
const consentInput = document.querySelector("#consent");
const requiredInputs = [fullNameInput, phoneInput, consentInput];

const API_BASE = window.DENTALAND_API_BASE || "http://127.0.0.1:8000";

const submitError = document.createElement("p");
submitError.className = "submit-error";
submitError.setAttribute("role", "alert");
submitError.hidden = true;
continueButton.insertAdjacentElement("afterend", submitError);

function formatDate(date) {
  return `${String(date.getDate()).padStart(2, "0")}.${String(date.getMonth() + 1).padStart(2, "0")}.${date.getFullYear()}. (${dayNames[date.getDay()]})`;
}

function toIsoDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function isMobile() {
  return window.matchMedia("(max-width: 767px)").matches;
}

function setStep(step, scrollOnMobile = true) {
  currentStep = step;

  document.querySelectorAll("[data-step-indicator]").forEach((indicator) => {
    const value = Number(indicator.dataset.stepIndicator);
    indicator.classList.toggle("active", value === step);
    if (value === step) indicator.setAttribute("aria-current", "step");
    else indicator.removeAttribute("aria-current");
  });

  document.querySelectorAll("[data-step-line]").forEach((line) => {
    line.classList.toggle("active", Number(line.dataset.stepLine) < step);
  });

  document.querySelectorAll("[data-step-card]").forEach((card) => {
    card.classList.toggle("current-step", Number(card.dataset.stepCard) === step);
  });

  if (scrollOnMobile && isMobile()) {
    document.querySelector(`[data-step-card="${step}"]`).scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }
}

function renderCalendar() {
  grid.replaceChildren();
  monthLabel.textContent = `${monthNames[displayedMonth.getMonth()]} ${displayedMonth.getFullYear()}`;

  const firstDay = new Date(displayedMonth.getFullYear(), displayedMonth.getMonth(), 1);
  const mondayBasedOffset = (firstDay.getDay() + 6) % 7;
  const calendarStart = new Date(
    displayedMonth.getFullYear(),
    displayedMonth.getMonth(),
    1 - mondayBasedOffset,
  );

  for (let index = 0; index < 42; index += 1) {
    const date = new Date(
      calendarStart.getFullYear(),
      calendarStart.getMonth(),
      calendarStart.getDate() + index,
    );
    const belongsToDisplayedMonth = date.getMonth() === displayedMonth.getMonth();

    if (!belongsToDisplayedMonth) {
      const adjacentDate = document.createElement("span");
      adjacentDate.className = "adjacent-month";
      adjacentDate.textContent = String(date.getDate());
      adjacentDate.setAttribute("aria-hidden", "true");
      grid.append(adjacentDate);
      continue;
    }

    const button = document.createElement("button");
    button.type = "button";
    button.textContent = String(date.getDate());
    button.disabled = date < today || date.getDay() === 0;
    button.setAttribute("aria-label", formatDate(date));

    if (date.getTime() === today.getTime()) {
      button.classList.add("today");
      button.setAttribute("aria-current", "date");
    }

    if (selectedDate && date.getTime() === selectedDate.getTime()) {
      button.classList.add("selected");
      button.setAttribute("aria-pressed", "true");
    }

    button.addEventListener("click", () => {
      selectedDate = date;
      selectedDateLabel.textContent = formatDate(date);
      renderCalendar();
      validateForm();
      setStep(2);
      fullNameInput.focus({ preventScroll: true });
    });
    grid.append(button);
  }

  const currentMonth = new Date(today.getFullYear(), today.getMonth(), 1);
  previousMonthButton.disabled = displayedMonth <= currentMonth;
}

function validateForm() {
  const requiredComplete = requiredInputs.every((input) => (
    input.type === "checkbox" ? input.checked : input.value.trim().length > 0
  ));
  const emailValid = emailInput.value.trim() === "" || emailInput.validity.valid;
  continueButton.disabled = !(selectedDate && requiredComplete && emailValid);
}

function showSubmitError(message) {
  submitError.textContent = message;
  submitError.hidden = false;
}

async function submitBookingRequest() {
  const response = await fetch(`${API_BASE}/api/booking-requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ime: fullNameInput.value.trim(),
      telefon: phoneInput.value.trim(),
      email: emailInput.value.trim(),
      requested_date: toIsoDate(selectedDate),
    }),
  });

  if (!response.ok) {
    if (response.status === 429) {
      throw new Error("Previše zahtjeva u kratkom periodu. Pokušajte ponovo za minut.");
    }
    throw new Error("Zahtjev nije uspio. Pokušajte ponovo ili nas nazovite direktno.");
  }
}

previousMonthButton.addEventListener("click", () => {
  displayedMonth = new Date(displayedMonth.getFullYear(), displayedMonth.getMonth() - 1, 1);
  renderCalendar();
});

nextMonthButton.addEventListener("click", () => {
  displayedMonth = new Date(displayedMonth.getFullYear(), displayedMonth.getMonth() + 1, 1);
  renderCalendar();
});

requiredInputs.forEach((input) => {
  input.addEventListener("input", validateForm);
  input.addEventListener("change", validateForm);
});
emailInput.addEventListener("input", validateForm);

document.querySelector("#header-booking-button").addEventListener("click", () => {
  document.querySelector("#date-card").scrollIntoView({ behavior: "smooth", block: "start" });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  validateForm();

  if (!selectedDate) {
    setStep(1);
    return;
  }
  if (continueButton.disabled) return;

  submitError.hidden = true;
  continueButton.disabled = true;
  continueButton.innerHTML = "Šaljem…";

  try {
    await submitBookingRequest();
    setStep(3);
  } catch (error) {
    showSubmitError(error instanceof Error ? error.message : "Zahtjev nije uspio.");
  } finally {
    continueButton.innerHTML = 'Nastavi <span aria-hidden="true">→</span>';
    validateForm();
  }
});

renderCalendar();
validateForm();
setStep(currentStep, false);
