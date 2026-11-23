// Shows the company / graduation fields only for the roles that need them.
(function () {
  var radios = document.querySelectorAll('input[name="role"]');
  var pro = document.getElementById('proFields');
  if (!pro || !radios.length) return;
  var companyCol = pro.querySelector('.col-md-7');

  function update() {
    var checked = document.querySelector('input[name="role"]:checked');
    var role = checked ? checked.value : 'student';
    pro.style.display = role === 'student' ? 'none' : '';
    var label = pro.querySelector('[name="company_name"]').closest('.mb-3').querySelector('label');
    if (label) label.firstChild.textContent = role === 'company' ? 'Company name ' : 'Current company ';
    var gradCol = pro.querySelector('[name="graduation_year"]').closest('.col-md-5');
    gradCol.style.display = role === 'alumni' ? '' : 'none';
    companyCol.className = role === 'alumni' ? 'col-md-7' : 'col-12';
  }

  radios.forEach(function (r) { r.addEventListener('change', update); });
  if (!document.querySelector('input[name="role"]:checked')) radios[0].checked = true;
  update();
})();
