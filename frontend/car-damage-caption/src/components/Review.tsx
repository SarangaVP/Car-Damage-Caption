import React, { useState, useEffect } from 'react';
import axios from 'axios';
import '../App.css';
import Toast from './Toast';

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

interface ToastMessage {
  id: number;
  message: string;
  type: 'success' | 'error' | 'info';
  duration?: number;
}

const API_BASE_URL = 'http://localhost:8000';

const Review: React.FC = () => {
  const [reviewData, setReviewData] = useState<ReviewData | null>(null);
  const [manualCaption, setManualCaption] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [toastId, setToastId] = useState<number>(0);
  const [currentActionToastId, setCurrentActionToastId] = useState<number | null>(null);

  useEffect(() => {
    fetchReview();
  }, []);

  const addToast = (
    message: string,
    type: 'success' | 'error' | 'info',
    duration: number = 3000,
    clearCurrentAction: boolean = false
  ) => {
    if (clearCurrentAction && currentActionToastId !== null) {
      setToasts((prevToasts) => prevToasts.filter((toast) => toast.id !== currentActionToastId));
      setCurrentActionToastId(null);
    }

    const newToast = { id: toastId, message, type, duration };
    setToasts((prevToasts) => [...prevToasts, newToast]);
    setToastId((prevId) => prevId + 1);

    if (duration === Infinity) {
      setCurrentActionToastId(toastId);
    }
  };

  const removeToast = (id: number) => {
    setToasts((prevToasts) => prevToasts.filter((toast) => toast.id !== id));
    if (id === currentActionToastId) {
      setCurrentActionToastId(null);
    }
  };

  const fetchReview = async () => {
    setIsLoading(true);
    try {
      const response = await axios.get<ReviewData>(`${API_BASE_URL}/review`);
      console.log('Fetch Review Response:', response.data);
      setReviewData(response.data);
      setManualCaption('');
    } catch (error) {
      addToast(`Error fetching review: ${(error as Error).message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCheck = async () => {
    if (!reviewData || isLoading) return;
    setIsLoading(true);
    addToast('Evaluating...', 'info', Infinity);
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
      addToast('Evaluation completed', 'success', 3000, true);
    } catch (error) {
      console.error('Check Error:', error);
      addToast(`Error checking: ${(error as Error).message}`, 'error', 3000, true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!reviewData || isLoading) return;
    setIsLoading(true);
    addToast('Saving...', 'info', Infinity);
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
      addToast(response.data.message || 'Saved successfully', 'success', 3000, true);
    } catch (error) {
      console.error('Save Error:', error);
      addToast(`Error saving: ${(error as Error).message}`, 'error', 3000, true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFolderUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setIsLoading(true);
    addToast('Uploading folder...', 'info', Infinity);
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

      addToast('Folder uploaded successfully! Fetching next image...', 'success', 3000, true);
      await fetchReview();
    } catch (error) {
      console.error('Folder Upload Error:', error);
      addToast(`Error uploading folder: ${(error as Error).message}`, 'error', 3000, true);
    } finally {
      setIsLoading(false);
      event.target.value = '';
    }
  };

  const handleDownloadJson = async () => {
    setIsLoading(true);
    addToast('Downloading JSON files...', 'info', Infinity);
    try {
      const response = await axios.get(`${API_BASE_URL}/download_json`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'car_damage_data.zip');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      addToast('JSON files downloaded successfully', 'success', 3000, true);
    } catch (error) {
      console.error('Download JSON Error:', error);
      addToast(`Error downloading JSON files: ${(error as Error).message}`, 'error', 3000, true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearJson = async () => {
    setIsLoading(true);
    addToast('Clearing JSON files...', 'info', Infinity);
    try {
      const response = await axios.post(`${API_BASE_URL}/clear_json`);
      addToast(response.data.message || 'JSON files cleared successfully', 'success', 3000, true);
      // Optionally refresh the review data to reflect the cleared state
      await fetchReview();
    } catch (error) {
      console.error('Clear JSON Error:', error);
      addToast(`Error clearing JSON files: ${(error as Error).message}`, 'error', 3000, true);
    } finally {
      setIsLoading(false);
    }
  };

  if (!reviewData) return <div className="spinner"></div>;

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
        <button
          className="btn btn-primary"
          onClick={handleDownloadJson}
          disabled={isLoading}
          style={{ marginLeft: '10px' }}
        >
          Download JSON Files
        </button>
        <button
          className="btn btn-secondary"
          onClick={handleClearJson}
          disabled={isLoading}
          style={{ marginLeft: '10px' }}
        >
          Clear JSON Files
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
          </div>
        </div>
      )}
      <div className="toast-container">
        {toasts.map((toast) => (
          <Toast
            key={toast.id}
            message={toast.message}
            type={toast.type}
            onClose={() => removeToast(toast.id)}
            duration={toast.duration}
          />
        ))}
      </div>
    </div>
  );
};

export default Review;