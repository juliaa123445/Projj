$(document).ready(function () {
    // Ukryj wszystkie modale na starcie
    $('.modal-content').hide();

    // Otwórz modal na podstawie klikniętego przycisku
    $('.menu-button').on('click', function () {
        const target = $(this).attr('id').replace('-button', '-content');
        $('.modal-content').hide();  // Ukryj inne modale
        $('#' + target).fadeIn();
    });

    // Zamknij modal po kliknięciu w tło
    $(window).on('click', function (event) {
        if ($(event.target).hasClass('modal-content')) {
            $('.modal-content').fadeOut();
        }
    });
});

// Hide flash messages on button click
$(document).ready(function () {
    // Hide flash messages when any menu button is clicked
    $('.menu-button').on('click', function () {
        $('#flash-messages').fadeOut();
    });

    // Fade out flash messages automatically after 5 seconds
    setTimeout(function() {
        $('#flash-messages').fadeOut('slow');
    }, 5000);
});

// Show flash messages initially if present, then hide on button click or timeout
$(document).ready(function () {
    // Hide flash messages on any button click
    $('.menu-button').on('click', function () {
        $('#flash-messages').fadeOut();
    });

    // Auto-hide flash messages after 5 seconds
    setTimeout(function() {
        $('#flash-messages').fadeOut('slow');
    }, 5000);
});



// Funkcja zamykająca modal na kliknięcie "X"
function closeModal(modalId) {
    $('#' + modalId).fadeOut();
}
