// static/script.js

document.addEventListener("DOMContentLoaded", function() {
  const attendanceDate = document.getElementById("attendance_date");
  if (attendanceDate) {
    let today = new Date();
    let year = today.getFullYear();
    let month = String(today.getMonth() + 1).padStart(2, '0');
    let day = String(today.getDate()).padStart(2, '0');
    attendanceDate.value = `${year}-${month}-${day}`;
  }
});
