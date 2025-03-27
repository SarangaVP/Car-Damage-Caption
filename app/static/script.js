document.getElementById('saveNext').addEventListener('click', function() {
    const caption = document.getElementById('caption').value;
    const imagePath = document.querySelector('img').src.split('/images/')[1];
    const status = document.getElementById('status');

    status.textContent = 'Saving...';

    fetch('/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ caption: caption, image_path: imagePath })
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
            document.getElementById('caption').value = data.caption;
            status.textContent = `Processed ${data.image_path} (Remaining: ${data.total})`;
        }
    })
    .catch(error => {
        status.textContent = 'Error: ' + error.message;
    });
});
