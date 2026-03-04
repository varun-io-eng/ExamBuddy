"""
file_processors.py - Audio and File Processing Utilities
NEW FILE - Add this to your project folder
"""

import streamlit as st
import os
import tempfile
from typing import Optional

class AudioProcessor:
    """Handle voice input processing"""
    
    @staticmethod
    def process_audio(audio_bytes) -> Optional[str]:
        """
        Convert audio to text using Google Speech Recognition
        Returns: Transcribed text or None if error
        """
        try:
            import speech_recognition as sr
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name
            
            # Initialize recognizer
            recognizer = sr.Recognizer()
            
            # Process audio
            with sr.AudioFile(tmp_path) as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio_data = recognizer.record(source)
                
                # Recognize speech (Google API)
                text = recognizer.recognize_google(audio_data)
                
            # Clean up temp file
            os.unlink(tmp_path)
            return text
            
        except ImportError:
            st.error("📦 Please install: pip install SpeechRecognition")
            return None
        except sr.UnknownValueError:
            st.error("🎤 Could not understand audio. Please speak clearly.")
            return None
        except sr.RequestError as e:
            st.error(f"🌐 Speech recognition service error: {e}")
            return None
        except Exception as e:
            st.error(f"❌ Audio processing error: {e}")
            return None


class FileProcessor:
    """Handle PDF and image file processing"""
    
    @staticmethod
    def process_pdf(uploaded_file) -> Optional[str]:
        """
        Extract text from PDF file
        Returns: Extracted text or None if error
        """
        try:
            import PyPDF2
            
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            
            # Extract text from all pages
            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}"
            
            if not text.strip():
                st.warning("⚠️ PDF appears to be image-based. Try uploading as image for OCR.")
                return None
            
            return text
            
        except ImportError:
            st.error("📦 Please install: pip install PyPDF2")
            return None
        except Exception as e:
            st.error(f"📄 PDF processing error: {e}")
            return None
    
    @staticmethod
    def process_image(uploaded_file) -> Optional[str]:
        """
        Extract text from image using OCR
        Returns: Extracted text or None
        """
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            import pytesseract
            
            # Open image
            image = Image.open(uploaded_file)
            
            # Preprocess for better OCR
            # Convert to grayscale
            image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2)
            
            # Sharpen
            image = image.filter(ImageFilter.SHARPEN)
            
            # Extract text
            text = pytesseract.image_to_string(image)
            
            if not text.strip():
                st.warning("⚠️ No text detected in image. Ensure image is clear and contains text.")
                return None
            
            return text
            
        except ImportError:
            st.error("📦 Please install: pip install pytesseract pillow")
            st.info("Also install Tesseract OCR: https://github.com/tesseract-ocr/tesseract")
            return None
        except Exception as e:
            st.error(f"🖼️ Image processing error: {e}")
            return None
    
    @staticmethod
    def process_file(uploaded_file) -> Optional[str]:
        """
        Main file processor - automatically detects type
        Returns: Extracted text or None
        """
        file_type = uploaded_file.type.lower()
        
        if "pdf" in file_type:
            return FileProcessor.process_pdf(uploaded_file)
        
        elif any(img_type in file_type for img_type in ["png", "jpg", "jpeg"]):
            return FileProcessor.process_image(uploaded_file)
        
        else:
            st.error(f"❌ Unsupported file type: {file_type}")
            st.info("Supported formats: PDF, PNG, JPG, JPEG")
            return None


class ContentAnalyzer:
    """Analyze extracted content"""
    
    @staticmethod
    def detect_content_type(text: str) -> str:
        """
        Detect what type of content was extracted
        """
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ['syllabus', 'curriculum', 'course outline']):
            return "📋 Syllabus"
        
        if any(kw in text_lower for kw in ['question', 'what is', 'explain', 'calculate']):
            return "❓ Question"
        
        if any(kw in text_lower for kw in ['chapter', 'notes', 'definition', 'theorem']):
            return "📝 Study Notes"
        
        return "📄 General Content"
    
    @staticmethod
    def get_word_count(text: str) -> int:
        """Get word count of text"""
        return len(text.split())
    
    @staticmethod
    def create_summary(text: str, max_chars: int = 200) -> str:
        """Create brief summary"""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."


# Example usage / testing
if __name__ == "__main__":
    st.title("🧪 File Processor Test")
    
    st.markdown("### Test Audio Processing")
    audio = st.audio_input("Record a test message")
    if audio:
        text = AudioProcessor.process_audio(audio)
        if text:
            st.success(f"Recognized: {text}")
    
    st.markdown("### Test File Upload")
    uploaded = st.file_uploader("Upload PDF or Image", type=['pdf', 'png', 'jpg', 'jpeg'])
    if uploaded:
        text = FileProcessor.process_file(uploaded)
        if text:
            content_type = ContentAnalyzer.detect_content_type(text)
            word_count = ContentAnalyzer.get_word_count(text)
            
            st.success(f"✅ Processed: {content_type}")
            st.info(f"📊 Word count: {word_count}")
            
            st.text_area("Extracted Text", text, height=300)