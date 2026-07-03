document.addEventListener('DOMContentLoaded', () => {
    // Read elements
    const timerText = document.getElementById('timer-text');
    const progressBar = document.getElementById('timer-progress-bar');
    const questionCards = document.querySelectorAll('.question-card');
    const navButtons = document.querySelectorAll('.question-nav-btn');
    const prevBtn = document.getElementById('prev-question-btn');
    const nextBtn = document.getElementById('next-question-btn');
    const submitSectionBtn = document.getElementById('submit-section-btn');

    if (!timerText) return; // Exit if not in exam interface

    // Parse state data injected from Django
    const sessionDataEl = document.getElementById('session-data');
    const sessionId = sessionDataEl.dataset.sessionId;
    const initialTimeLeft = parseInt(sessionDataEl.dataset.timeLeft, 10);
    const sectionDuration = parseInt(sessionDataEl.dataset.sectionDuration, 10);
    const activeSectionId = sessionDataEl.dataset.sectionId;
    const savedAnswers = JSON.parse(document.getElementById('saved-answers-json').textContent || '{}');

    let activeQuestionIndex = 0;
    let secondsLeft = initialTimeLeft;

    // Load saved answers into options input states on load
    Object.keys(savedAnswers).forEach(qId => {
        const optionIds = savedAnswers[qId];
        optionIds.forEach(optId => {
            const input = document.querySelector(`input[name="q_${qId}"][value="${optId}"]`);
            if (input) {
                input.checked = true;
                input.closest('.option-wrapper').classList.add('checked');
            }
        });
        
        // Color nav button as answered
        const navBtn = document.querySelector(`.question-nav-btn[data-question-id="${qId}"]`);
        if (navBtn && optionIds.length > 0) {
            navBtn.classList.add('answered');
        }
    });

    // Real-time progress updater for the right sidebar sections list
    function updateSectionProgress() {
        if (!activeSectionId) return;
        const totalQuestions = questionCards.length;
        let answeredQuestionsCount = 0;
        
        questionCards.forEach(card => {
            const checked = card.querySelectorAll('input:checked');
            if (checked.length > 0) {
                answeredQuestionsCount++;
            }
        });

        const remainingQuestionsCount = totalQuestions - answeredQuestionsCount;

        const attemptCntEl = document.getElementById(`sec-attempt-cnt-${activeSectionId}`);
        const remCntEl = document.getElementById(`sec-rem-cnt-${activeSectionId}`);

        if (attemptCntEl) {
            attemptCntEl.textContent = `Attempted: ${answeredQuestionsCount} / ${totalQuestions}`;
        }
        if (remCntEl) {
            remCntEl.textContent = `${remainingQuestionsCount} remaining`;
            if (remainingQuestionsCount > 0) {
                remCntEl.style.color = 'var(--accent-cyan)';
            } else {
                remCntEl.style.color = 'var(--text-muted)';
            }
        }
    }

    // Run once on load
    updateSectionProgress();

    // Display active question
    function showQuestion(index) {
        questionCards.forEach((card, idx) => {
            card.style.display = idx === index ? 'block' : 'none';
        });

        navButtons.forEach((btn, idx) => {
            btn.classList.toggle('active', idx === index);
        });

        // Update button actions
        prevBtn.style.display = index === 0 ? 'none' : 'inline-flex';
        
        if (index === questionCards.length - 1) {
            nextBtn.style.display = 'none';
            submitSectionBtn.style.display = 'inline-flex';
        } else {
            nextBtn.style.display = 'inline-flex';
            submitSectionBtn.style.display = 'none';
        }

        activeQuestionIndex = index;
    }

    // Initialize display
    if (questionCards.length > 0) {
        showQuestion(0);
    }

    // Navigation triggers
    prevBtn.addEventListener('click', () => {
        if (activeQuestionIndex > 0) showQuestion(activeQuestionIndex - 1);
    });

    nextBtn.addEventListener('click', () => {
        if (activeQuestionIndex < questionCards.length - 1) showQuestion(activeQuestionIndex + 1);
    });

    navButtons.forEach((btn, idx) => {
        btn.addEventListener('click', () => showQuestion(idx));
    });

    // Auto-save changes on option selection clicks
    document.querySelectorAll('.option-input').forEach(input => {
        input.addEventListener('change', (e) => {
            const wrapper = e.target.closest('.option-wrapper');
            const questionId = e.target.name.split('_')[1];
            
            // Toggle wrapper active highlighting
            if (e.target.type === 'radio') {
                // Clear sibling option highlighted wrapper borders
                document.querySelectorAll(`input[name="q_${questionId}"]`).forEach(rad => {
                    rad.closest('.option-wrapper').classList.toggle('checked', rad.checked);
                });
            } else {
                wrapper.classList.toggle('checked', e.target.checked);
            }

            // Read all checked option values
            const checkedInputs = document.querySelectorAll(`input[name="q_${questionId}"]:checked`);
            const selectedOptionIds = Array.from(checkedInputs).map(i => parseInt(i.value, 10));

            // Mark nav button state
            const navBtn = document.querySelector(`.question-nav-btn[data-question-id="${questionId}"]`);
            if (navBtn) {
                navBtn.classList.toggle('answered', selectedOptionIds.length > 0);
            }

            // Update sections list attempted / remaining stats on the right sidebar
            updateSectionProgress();

            // Dispatch background AJAX save API
            fetch(`/session/${sessionId}/save-answers/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    question_id: parseInt(questionId, 10),
                    option_ids: selectedOptionIds
                })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status !== 'success') {
                    console.error('Error saving answers:', data.message);
                }
            })
            .catch(err => console.error('Save request failed:', err));
        });
    });

    // Section Submission handler
    function submitSection() {
        // Collect all answers on this page to ensure everything is saved
        const answers = {};
        questionCards.forEach(card => {
            const qId = card.dataset.questionId;
            const checked = card.querySelectorAll('input:checked');
            answers[qId] = Array.from(checked).map(i => parseInt(i.value, 10));
        });

        // Trigger loading screen
        document.body.style.opacity = '0.7';
        document.body.style.pointerEvents = 'none';

        fetch(`/session/${sessionId}/submit-section/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ answers })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                window.location.href = data.next_url;
            } else {
                alert('Submission failed. Please check network and try again.');
                document.body.style.opacity = '1';
                document.body.style.pointerEvents = 'auto';
            }
        })
        .catch(err => {
            console.error('Submit request failed:', err);
            alert('Submission failed. Please try again.');
            document.body.style.opacity = '1';
            document.body.style.pointerEvents = 'auto';
        });
    }

    submitSectionBtn.addEventListener('click', () => {
        if (confirm("Are you sure you want to complete this section? You will not be able to return to it.")) {
            submitSection();
        }
    });

    // Timer Countdown Loop
    const timerInterval = setInterval(() => {
        secondsLeft--;

        if (secondsLeft <= 0) {
            clearInterval(timerInterval);
            timerText.textContent = "TIME UP!";
            progressBar.style.width = "0%";
            
            // Auto submit section
            submitSection();
        } else {
            // Update Text
            const mins = Math.floor(secondsLeft / 60);
            const secs = secondsLeft % 60;
            timerText.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

            // Update Progress bar
            const pct = (secondsLeft / sectionDuration) * 100;
            progressBar.style.width = `${pct}%`;

            // Style warning if under 60 seconds
            if (secondsLeft <= 60) {
                timerText.style.color = 'var(--accent-rose)';
                progressBar.style.background = 'var(--accent-rose)';
            }
        }
    }, 1000);

    // Cookie reader helper
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
