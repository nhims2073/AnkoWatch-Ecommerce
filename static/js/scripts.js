function decreaseQuantity(button) {
    let input = button.parentNode.querySelector('input[type=number]');
    if (input.value > 1) {
        input.stepDown();
    }
}

function increaseQuantity(button) {
    let input = button.parentNode.querySelector('input[type=number]');
    if (input.value < 99) {
        input.stepUp();
    }
}

// Get the button
let mybutton = document.getElementById("myBtn");

// When the user scrolls down 20px from the top of the document, show the button
window.onscroll = function() {scrollFunction()};

function scrollFunction() {
  if (document.body.scrollTop > 70 || document.documentElement.scrollTop > 70) {
    mybutton.style.display = "block";
  } else {
    mybutton.style.display = "none";
  }
}

// When the user clicks on the button, scroll to the top of the document
function topFunction() {
  document.body.scrollTop = 0;
  document.documentElement.scrollTop = 0;
}

function updateDropdown(buttonId, value) {
  document.getElementById(buttonId).innerText = value;
}