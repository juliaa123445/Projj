$(document).ready(function () {
    $('.modal-content').hide();

    $('.menu-button').on('click', function () {
        const target = $(this).attr('id').replace('-button', '-content');
        $('.modal-content').hide();
        $('#' + target).fadeIn();
    });

    $(window).on('click', function (event) {
        if ($(event.target).hasClass('modal-content')) {
            $('.modal-content').fadeOut();
        }
    });

    $('.menu-button').hover(function(){
        $(this).animate({padding: '12px 24px'}, 200);
    }, function(){
        $(this).animate({padding: '10px 20px'}, 200);
    });

    $('.menu-button').on('click', function () {
        $('#flash-messages').fadeOut();
    });

    setTimeout(function() {
        $('#flash-messages').fadeOut('slow');
    }, 5000);

    $('#scale').on('change', function () {
        const selectedScale = parseInt($(this).val());

        $('#options-container .option-field').each(function (index) {
            if (index < selectedScale) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    }).trigger('change');
});

function closeModal(modalId) {
    $('#' + modalId).fadeOut();
}

const charts = {};

function createChart(surveyId, labels, data) {
    const ctx = document.getElementById(`votesChart${surveyId}`).getContext('2d');
    charts[surveyId] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Votes',
                data: data,
                backgroundColor: 'rgba(75, 192, 192, 0.6)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    grid: { display: false }
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Ilość głosów' },
                    grid: { color: '#ddd' },
                    ticks: {
                        stepSize: function(context) {
                            const maxVotes = Math.max(...data);
                            if (maxVotes > 500) return 100;
                            if (maxVotes > 100) return 50;
                            if (maxVotes > 50) return 20;
                            if (maxVotes > 20) return 10;
                            if (maxVotes > 10) return 5;
                            if (maxVotes > 5) return 2;
                            return 1;
                        }
                    }
                }
            }
        }
    });
}

function updateCharts() {
    fetch('/api/votes')
        .then(response => response.json())
        .then(data => {
            const surveyData = {};

            data.forEach(vote => {
                if (!surveyData[vote.survey_id]) {
                    surveyData[vote.survey_id] = { labels: [], votes: [] };
                }
                surveyData[vote.survey_id].labels.push(vote.score); // Use option names as labels
                surveyData[vote.survey_id].votes.push(vote.votes);
            });

            Object.keys(surveyData).forEach(surveyId => {
                if (charts[surveyId]) {
                    charts[surveyId].data.labels = surveyData[surveyId].labels;
                    charts[surveyId].data.datasets[0].data = surveyData[surveyId].votes;
                    charts[surveyId].update();
                } else {
                    createChart(surveyId, surveyData[surveyId].labels, surveyData[surveyId].votes);
                }
            });
        });
}

setInterval(updateCharts, 5000);
updateCharts();
