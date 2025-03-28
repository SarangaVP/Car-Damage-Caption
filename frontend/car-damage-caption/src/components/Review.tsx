import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../App.css';

interface ReviewData {
  image_path: string;
  gemma_caption: string;
  total: number;
  gemma_score?: number | null;
  gemma_explanation?: string;
  manual_score?: number | null;
  manual_explanation?: string;
  message?: string;
  done?: boolean;
}

const API_BASE_URL = 'http://localhost:8000';

const Review: React.FC = () => {
  const [reviewData, setReviewData] = useState<ReviewData | null>(null);
  const [manualCaption, setManualCaption] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  useEffect(() => {
    fetchReview();
  }, []);

  const fetchReview = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get<ReviewData>(`${API_BASE_URL}/review`);
      console.log('Fetch Review Response:', response.data);
      setReviewData(response.data);
      setManualCaption('');
      setStatus('');
    } catch (error) {
      setStatus(`Error fetching review: ${(error as Error).message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCheck = async () => {
    if (!reviewData || isLoading) return;
    setIsLoading(true);
    setStatus('Evaluating...');
    try {
      const response = await axios.post<Partial<ReviewData>>(`${API_BASE_URL}/review`, {
        action: 'check',
        image_path: reviewData.image_path,
        gemma_caption: reviewData.gemma_caption,
        manual_caption: manualCaption,
      });
      console.log('Check Response:', response.data);
      const updatedData = {
        ...reviewData,
        gemma_score: response.data.gemma_score ?? null,
        gemma_explanation: response.data.gemma_explanation ?? '',
        manual_score: response.data.manual_score ?? null,
        manual_explanation: response.data.manual_explanation ?? '',
      };
      setReviewData(updatedData);
      console.log('Updated reviewData:', updatedData);
      setStatus('');
    } catch (error) {
      console.error('Check Error:', error);
      setStatus(`Error checking: ${(error as Error).message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!reviewData || isLoading) return;
    setIsLoading(true);
    setStatus('Saving...');
    try {
      const response = await axios.post<ReviewData>(`${API_BASE_URL}/review`, {
        action: 'save',
        image_path: reviewData.image_path,
        gemma_caption: reviewData.gemma_caption,
        manual_caption: manualCaption,
        gemma_score: reviewData.gemma_score,
        manual_score: reviewData.manual_score,
      });
      console.log('Save Response:', response.data);
      if (response.data.done) {
        setReviewData({ ...response.data, image_path: '', gemma_caption: '' });
      } else {
        setReviewData({ ...response.data, gemma_score: null, manual_score: null });
        setManualCaption('');
      }
      setStatus(response.data.message || 'Saved successfully');
    } catch (error) {
      console.error('Save Error:', error);
      setStatus(`Error saving: ${(error as Error).message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFolderUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setIsLoading(true);
    setStatus('Uploading folder...');

    try {
      const formData = new FormData();
      Array.from(files).forEach((file) => {
        formData.append('files', file, file.webkitRelativePath || file.name);
      });

      await axios.post(`${API_BASE_URL}/upload_folder`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setStatus('Folder uploaded successfully! Fetching next image...');
      await fetchReview();
    } catch (error) {
      console.error('Folder Upload Error:', error);
      setStatus(`Error uploading folder: ${(error as Error).message}`);
    } finally {
      setIsLoading(false);
      event.target.value = '';
    }
  };

  const handleDownloadJson = async () => {
    setIsLoading(true);
    setStatus('Downloading JSON files...');
    try {
      const response = await axios.get(`${API_BASE_URL}/download_json`, {
        responseType: 'blob', // Important for handling binary data (ZIP file)
      });

      // Create a URL for the blob and trigger the download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'car_damage_data.zip'); // Match the filename from the backend
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url); // Clean up the URL object

      setStatus('JSON files downloaded successfully');
    } catch (error) {
      console.error('Download JSON Error:', error);
      setStatus(`Error downloading JSON files: ${(error as Error).message}`);
    } finally {
      setIsLoading(false);
    }
  };

  if (!reviewData && !status) return <div className="spinner"></div>;

  return (
    <div className="container">
      <h1>Car Damage Review</h1>
      <div className="folder-upload-section">
        <label htmlFor="folder-upload">Upload a Folder of Images</label>
        <input
          type="file"
          id="folder-upload"
          // @ts-ignore: webkitdirectory is a non-standard attribute
          webkitdirectory="true"
          directory="true"
          onChange={handleFolderUpload}
          disabled={isLoading}
        />
        {/* Added Download JSON Files button */}
        <button
          className="btn btn-primary"
          onClick={handleDownloadJson}
          disabled={isLoading}
          style={{ marginLeft: '10px' }}
        >
          Download JSON Files
        </button>
      </div>
      {reviewData?.done ? (
        <div className="done-message">
          <p>{reviewData.message}</p>
          <a href="/" className="btn btn-primary">Back to Home</a>
        </div>
      ) : (
        <div className="review-grid">
          <div className="image-section">
            <div className="image-container">
              <img src={`${API_BASE_URL}/images/${reviewData?.image_path}`} alt="Car" />
            </div>
            <p className="image-info">
              Processing image: {reviewData?.image_path} (Remaining: {reviewData?.total})
            </p>
          </div>
          <div className="form-section">
            <div className="description-card">
              <label htmlFor="gemma_caption">Generated Description</label>
              <textarea
                id="gemma_caption"
                rows={5}
                value={reviewData?.gemma_caption || ''}
                onChange={(e) => setReviewData({ ...reviewData!, gemma_caption: e.target.value })}
              />
              <div className="evaluation">
                <p><strong>Evaluation</strong></p>
                <p>Score: {reviewData?.gemma_score !== undefined && reviewData.gemma_score !== null ? `${reviewData.gemma_score}/5` : 'Not evaluated'}</p>
                {reviewData?.gemma_explanation && <p>{reviewData.gemma_explanation}</p>}
              </div>
            </div>
            <div className="description-card">
              <label htmlFor="manual_caption">Manual Description</label>
              <textarea
                id="manual_caption"
                rows={5}
                value={manualCaption}
                onChange={(e) => setManualCaption(e.target.value)}
                placeholder="Type your own caption here"
              />
              <div className="evaluation">
                <p><strong>Evaluation</strong></p>
                <p>Score: {reviewData?.manual_score !== undefined && reviewData.manual_score !== null ? `${reviewData.manual_score}/5` : 'Not evaluated'}</p>
                {reviewData?.manual_explanation && <p>{reviewData.manual_explanation}</p>}
              </div>
            </div>
            <div className="button-group">
              <button className="btn btn-primary" onClick={handleCheck} disabled={isLoading}>
                Evaluate
              </button>
              <button className="btn btn-secondary" onClick={handleSave} disabled={isLoading}>
                Save and Next
              </button>
            </div>
            {status && <p className="status">{status}</p>}
          </div>
        </div>
      )}
    </div>
  );
};

export default Review;