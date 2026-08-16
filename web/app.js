const monthNames=["Januar","Februar","Mart","April","Maj","Juni","Juli","Avgust","Septembar","Oktobar","Novembar","Decembar"];
const dayNames=["nedjelja","ponedjeljak","utorak","srijeda","četvrtak","petak","subota"];
const today=new Date();today.setHours(0,0,0,0);let displayedMonth=new Date(today.getFullYear(),today.getMonth(),1);let selectedDate=null;let currentStep=1;
const grid=document.querySelector("#calendar-grid"),monthLabel=document.querySelector("#month-label"),form=document.querySelector("#booking-form"),continueButton=document.querySelector("#continue-button");
const requiredInputs=[document.querySelector("#full-name"),document.querySelector("#phone"),document.querySelector("#consent")];
function setStep(step){currentStep=step;document.querySelectorAll("[data-step-indicator]").forEach(indicator=>{const value=Number(indicator.dataset.stepIndicator);indicator.classList.toggle("is-active",value===step);indicator.classList.toggle("is-complete",value<step);if(value===step)indicator.setAttribute("aria-current","step");else indicator.removeAttribute("aria-current")});document.querySelectorAll("[data-panel]").forEach(panel=>panel.classList.toggle("is-current",Number(panel.dataset.panel)===step));if(window.matchMedia("(max-width: 767px)").matches)document.querySelector(`[data-panel="${step}"]`).scrollIntoView({behavior:"smooth",block:"start"})}
function formatDate(date){return `${String(date.getDate()).padStart(2,"0")}.${String(date.getMonth()+1).padStart(2,"0")}.${date.getFullYear()}. (${dayNames[date.getDay()]})`}
function renderCalendar(){grid.replaceChildren();monthLabel.textContent=`${monthNames[displayedMonth.getMonth()]} ${displayedMonth.getFullYear()}`;const first=new Date(displayedMonth.getFullYear(),displayedMonth.getMonth(),1),last=new Date(displayedMonth.getFullYear(),displayedMonth.getMonth()+1,0),fgd=first.getDay(),offset=(fgd===0||fgd===6)?0:fgd-1;for(let i=0;i<offset;i+=1){const empty=document.createElement("span");empty.className="empty";grid.append(empty)}for(let day=1;day<=last.getDate();day+=1){const date=new Date(displayedMonth.getFullYear(),displayedMonth.getMonth(),day);if(date.getDay()===0||date.getDay()===6)continue;const button=document.createElement("button");button.type="button";button.textContent=String(day);button.disabled=date<today;button.setAttribute("aria-label",formatDate(date));if(selectedDate&&date.getTime()===selectedDate.getTime())button.classList.add("is-selected");button.addEventListener("click",()=>{selectedDate=date;document.querySelector("#selected-date").textContent=formatDate(date);renderCalendar();setStep(2);document.querySelector("#full-name").focus({preventScroll:true})});grid.append(button)}}
function validateForm(){continueButton.disabled=!requiredInputs.every(input=>input.type==="checkbox"?input.checked:input.value.trim().length>0)}

// DENT-007 — lokalni backend (uvicorn backend.main:app, radi na 127.0.0.1:8000).
// Nema javnog hostinga, nema tokena, nema RBAC-a — vidi backend/main.py docstring.
const API_BASE="http://127.0.0.1:8000";
const submitError=document.createElement("p");
submitError.className="submit-error";
submitError.setAttribute("role","alert");
submitError.hidden=true;
submitError.style.cssText="color:#d74646;font-size:13px;margin-top:9px";
continueButton.insertAdjacentElement("afterend",submitError);
function toIsoDate(date){return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,"0")}-${String(date.getDate()).padStart(2,"0")}`}
function showSubmitError(message){submitError.textContent=message;submitError.hidden=false}
async function submitBookingRequest(){
  const response=await fetch(`${API_BASE}/api/booking-requests`,{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      ime:document.querySelector("#full-name").value.trim(),
      telefon:document.querySelector("#phone").value.trim(),
      email:document.querySelector("#email").value.trim(),
      requested_date:toIsoDate(selectedDate),
    }),
  });
  if(!response.ok){
    if(response.status===429)throw new Error("Previše zahtjeva u kratkom periodu. Pokušajte ponovo za minut.");
    throw new Error("Zahtjev nije uspio. Provjerite internet konekciju i pokušajte ponovo, ili nas nazovite direktno.");
  }
}
document.querySelector("#previous-month").addEventListener("click",()=>{displayedMonth=new Date(displayedMonth.getFullYear(),displayedMonth.getMonth()-1,1);renderCalendar()});document.querySelector("#next-month").addEventListener("click",()=>{displayedMonth=new Date(displayedMonth.getFullYear(),displayedMonth.getMonth()+1,1);renderCalendar()});requiredInputs.forEach(input=>{input.addEventListener("input",validateForm);input.addEventListener("change",validateForm)});form.addEventListener("submit",async event=>{event.preventDefault();validateForm();if(!selectedDate){setStep(1);return}if(continueButton.disabled)return;submitError.hidden=true;continueButton.disabled=true;continueButton.textContent="Šaljem...";try{await submitBookingRequest();setStep(3)}catch(error){showSubmitError(error.message)}finally{continueButton.disabled=false;continueButton.innerHTML='Nastavi <span aria-hidden="true">→</span>'}});renderCalendar();validateForm();setStep(currentStep);
