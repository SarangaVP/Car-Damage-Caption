document.getElementById('checkButton').addEventListener('click', function() {
    const gemmaCaption = document.getElementById('gemma_caption').value;
    const manualCaption = document.getElementById('manual_caption').value;
    const imagePath = document.querySelector('img').src.split('/images/')[1];
    const status = document.getElementById('status');

    status.textContent = 'Checking with Pixtral...';

    fetch('/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            action: 'check',
            image_path: imagePath,
            gemma_caption: gemmaCaption,
            manual_caption: manualCaption
        })
    })
    .then(response => response.json())
    .then(data => {
        status.textContent = '';
        document.getElementById('gemma_evaluation').innerHTML = data.gemma_score !== null 
            ? `<p><strong>Pixtral Evaluation:</strong></p><p>Score: ${data.gemma_score}/5</p><p>${data.gemma_explanation}</p>`
            : `<p><strong>Pixtral Evaluation:</strong></p><p>Score: Not available</p><p>${data.gemma_explanation}</p>`;
        document.getElementById('manual_evaluation').innerHTML = data.manual_score !== null 
            ? `<p><strong>Pixtral Evaluation:</strong></p><p>Score: ${data.manual_score}/5</p><p>${data.manual_explanation}</p>`
            : `<p><strong>Pixtral Evaluation:</strong></p><p>Score: Not available</p><p>${data.manual_explanation}</p>`;
    })
    .catch(error => {
        status.textContent = 'Error: ' + error.message;
    });
});

document.getElementById('saveNext').addEventListener('click', function() {
    const gemmaCaption = document.getElementById('gemma_caption').value;
    const manualCaption = document.getElementById('manual_caption').value;
    const imagePath = document.querySelector('img').src.split('/images/')[1];
    const status = document.getElementById('status');
    const gemmaScore = document.getElementById('gemma_evaluation').querySelector('p:nth-child(2)')?.textContent.split(': ')[1]?.split('/')[0] || null;
    const manualScore = document.getElementById('manual_evaluation').querySelector('p:nth-child(2)')?.textContent.split(': ')[1]?.split('/')[0] || null;

    status.textContent = 'Saving...';

    fetch('/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            action: 'save',
            image_path: imagePath,
            gemma_caption: gemmaCaption,
            manual_caption: manualCaption,
            gemma_score: gemmaScore ? parseInt(gemmaScore) : null,
            manual_score: manualScore ? parseInt(manualScore) : null
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.done) {
            status.textContent = data.message;
            document.getElementById('saveNext').style.display = 'none';
            document.querySelector('.container').innerHTML += '<a href="/" class="btn">Back to Home</a>';
        } else if (data.error) {
            status.textContent = data.error;
        } else {
            document.querySelector('img').src = '/images/' + data.image_path;
            document.getElementById('gemma_caption').value = data.caption;
            document.getElementById('manual_caption').value = '';
            document.getElementById('gemma_evaluation').innerHTML = '';
            document.getElementById('manual_evaluation').innerHTML = '';
            status.textContent = `Processed ${data.image_path} (Remaining: ${data.total})`;
        }
    })
    .catch(error => {
        status.textContent = 'Error: ' + error.message;
    });
});