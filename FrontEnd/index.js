// API Base URL - Change this to your API endpoint
const API_BASE_URL = 'http://localhost:8000'

// Elements
const personInput = document.getElementById('personInput')
const garmentInput = document.getElementById('garmentInput')
const personDropzone = document.getElementById('personDropzone')
const garmentDropzone = document.getElementById('garmentDropzone')
const generateButton = document.getElementById('generateButton')
const generatedImageContainer = document.getElementById(
  'generatedImageContainer'
)
const analysisBox = document.getElementById('analysisBox')

// State
let personImage = null
let garmentImage = null
let personFile = null
let garmentFile = null
let tryOnResultId = null
let isGenerating = false

// Event listeners
personInput.addEventListener('change', handlePersonImageUpload)

garmentInput.addEventListener('change', handleGarmentImageUpload)

generateButton.addEventListener('click', (event) => {
  event.preventDefault()
  handleGenerate()
})

// Add drag and drop functionality
setupDragAndDrop(personDropzone, personInput)
setupDragAndDrop(garmentDropzone, garmentInput)

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

function checkFiles() {
  const generateButton = document.getElementById('generateButton')
  generateButton.disabled = !(personFile && garmentFile)
}

function displayUploadedImage(dropzone, inputElement, imageUrl) {

  dropzone.classList.add('has-image');
  // Clear only the previous image and badge
  dropzone
    .querySelectorAll('.uploaded-image, .badge')
    .forEach((el) => el.remove())

  // Create image element and allow clicking it to re-upload
  const img = document.createElement('img')
  img.src = imageUrl
  img.className = 'uploaded-image'
  img.addEventListener('click', () => inputElement.click())
  dropzone.appendChild(img)

  // Add checkmark badge
  const badge = document.createElement('div')
  badge.className = 'badge'
  // ... (badge styling can remain the same)
  badge.style.position = 'absolute'
  badge.style.top = '10px'
  badge.style.right = '10px'
  badge.style.background = '#FF6B98'
  badge.style.color = 'white'
  badge.style.borderRadius = '50%'
  badge.style.width = '30px'
  badge.style.height = '30px'
  badge.style.display = 'flex'
  badge.style.alignItems = 'center'
  badge.style.justifyContent = 'center'
  badge.innerHTML = '<i class="fas fa-check"></i>'
  dropzone.appendChild(badge)
}

// Toast notification function
function showToast(message, type = 'info') {
  const toast = document.createElement('div')
  toast.className = `toast toast-${type}`
  toast.textContent = message
  document.body.appendChild(toast)

  // Animate in
  setTimeout(() => {
    toast.style.transform = 'translateY(0)'
    toast.style.opacity = '1'
  }, 50)

  // Remove after 3 seconds
  setTimeout(() => {
    toast.style.opacity = '0'
    toast.style.transform = 'translateY(-20px)'
    setTimeout(() => {
      document.body.removeChild(toast)
    }, 300)
  }, 3000)
}

// Functions
function setupDragAndDrop(dropzone, input) {
  ;['dragenter', 'dragover', 'dragleave', 'drop'].forEach((eventName) => {
    dropzone.addEventListener(
      eventName,
      (e) => {
        e.preventDefault()
        e.stopPropagation()
      },
      false
    )
  })
  ;['dragenter', 'dragover'].forEach((eventName) => {
    dropzone.addEventListener(
      eventName,
      () => dropzone.classList.add('highlight'),
      false
    )
  })
  ;['dragleave', 'drop'].forEach((eventName) => {
    dropzone.addEventListener(
      eventName,
      () => dropzone.classList.remove('highlight'),
      false
    )
  })
  dropzone.addEventListener(
    'drop',
    (e) => {
      const dt = e.dataTransfer
      const files = dt.files
      if (files && files.length) {
        input.files = files
        input.dispatchEvent(new Event('change'))
      }
    },
    false
  )
}

async function handlePersonImageUpload(e) {
  if (e.target.files && e.target.files[0]) {
    const file = e.target.files[0]
    personFile = file

    // Convert to Data URL for storage
    const imageUrl = await fileToDataUrl(file)
    localStorage.setItem('personImageUrl', imageUrl)
    personImage = imageUrl

    displayUploadedImage(personDropzone, personInput, imageUrl)
    checkEnableGenerate()
  }
}

async function handleGarmentImageUpload(e) {
  if (e.target.files && e.target.files[0]) {
    const file = e.target.files[0]
    garmentFile = file

    // Convert to Data URL for storage
    const imageUrl = await fileToDataUrl(file)
    localStorage.setItem('garmentImageUrl', imageUrl)
    garmentImage = imageUrl

    displayUploadedImage(garmentDropzone, garmentInput, imageUrl)
    checkEnableGenerate()
  }
}

function checkEnableGenerate() {
  if (personFile && garmentFile) {
    generateButton.disabled = false
    generateButton.classList.add('ready')
  } else {
    generateButton.disabled = true
    generateButton.classList.remove('ready')
  }

  if (personImage && garmentImage) {
    generateButton.disabled = false
    generateButton.innerHTML =
      '<i class="fas fa-wand-magic-sparkles"></i> Create Magic!'

    // Add a little animation
    generateButton.classList.add('ready')
    generateButton.style.animation = 'pulse 1.5s infinite'

    // Define pulse animation
    if (!document.getElementById('pulse-animation')) {
      const style = document.createElement('style')
      style.id = 'pulse-animation'
      style.textContent = `
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                    100% { transform: scale(1); }
                }
            `
      document.head.appendChild(style)
    }
  } else {
    generateButton.disabled = true
    generateButton.innerHTML =
      '<i class="fas fa-wand-magic-sparkles"></i> Create Magic!'
    generateButton.style.animation = 'none'
  }
}

async function handleGenerate() {
  if (isGenerating) return

  if (!personFile || !garmentFile) {
    showToast('Please upload both person and garment images', 'error')
    return
  }

  isGenerating = true
  generateButton.disabled = true
  generateButton.innerHTML =
    '<i class="fas fa-spinner fa-spin"></i> Processing...'

  // Show loading state with animation
  generatedImageContainer.innerHTML = `
        <div class="image-placeholder">
            <div style="position: relative; width: 60px; height: 60px;">
                <div style="position: absolute; border: 4px solid #FFE6F2; border-top: 4px solid #FF6B98; border-radius: 50%; width: 60px; height: 60px; animation: spin 1s linear infinite;"></div>
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 1.5rem;"><i class="fas fa-magic"></i></div>
            </div>
            <p style="margin-top: 20px; font-weight: 500; color: #FF6B98;">Creating your fashion magic...</p>
        </div>
    `

  // Define animation
  if (!document.getElementById('spin-animation')) {
    const style = document.createElement('style')
    style.id = 'spin-animation'
    style.textContent = `
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `
    document.head.appendChild(style)
  }

  try {
    const formData = new FormData()
    formData.append('person_image', personFile)
    formData.append('clothing_image', garmentFile)
    formData.append('user_id', 0)

    const response = await fetch(`${API_BASE_URL}/api/try-on/full-process`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      throw new Error(
        `Process failed: ${response.status} ${response.statusText}`
      )
    }

    const result = await response.json()
    console.log('Full process result:', result.result_url)
    localStorage.setItem('generatedImageUrl', result.result_url)

    const generatedImg = document.createElement('img')
    generatedImg.src = result.result_url
    generatedImg.className = 'generated-image'

    generatedImageContainer.innerHTML = ''
    generatedImageContainer.appendChild(generatedImg)
  } catch (error) {
    console.error('Error:', error)
    showToast(error.message, 'error')
    generatedImageContainer.innerHTML = `<div class="image-placeholder"><p>An error occurred. Please try again.</p></div>`
  } finally {
    isGenerating = false
    checkEnableGenerate()
    generateButton.innerHTML =
      '<i class="fas fa-wand-magic-sparkles"></i> Create Magic!'
  }
}

async function getFashionFeedback(resultId) {
  try {
    // Show loading in the analysis box
    document.querySelector('.analysis-content').innerHTML = `
            <div style="display: flex; justify-content: center; align-items: center; flex-direction: column; padding: 20px;">
                <div style="position: relative; width: 40px; height: 40px; margin-bottom: 15px;">
                    <div style="position: absolute; border: 3px solid #FFE6F2; border-top: 3px solid #FF6B98; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite;"></div>
                </div>
                <p>Analyzing your fashion fit...</p>
            </div>
        `

    // Get feedback
    const feedbackResponse = await fetch(
      `${API_BASE_URL}/api/feedback/${resultId}`,
      {
        method: 'GET',
      }
    )

    if (!feedbackResponse.ok) {
      throw new Error(`API Error: ${feedbackResponse.status}`)
    }

    const data = await feedbackResponse.json()
    const feedback = data.data.feedback
    const formattedText = data.data.formatted_text

    // If we have formatted text from the server, use it
    if (formattedText) {
      // Split by double newlines to get sections
      const sections = formattedText.split('\n\n')
      let analysisContent = ''

      sections.forEach((section) => {
        const lines = section.split('\n')
        const title = lines[0]
        const details = lines.slice(1)

        analysisContent += `<div class="feedback-section">
                    <h3 style="color: #FF6B98; margin-bottom: 10px;">${title}</h3>`

        if (details.length > 0) {
          details.forEach((detail) => {
            analysisContent += `<p style="margin-bottom: 5px;">${detail}</p>`
          })
        }

        analysisContent += `</div>`
      })

      document.querySelector('.analysis-content').innerHTML = analysisContent
    } else {
      // Fallback to manual formatting if formatted text is not available
      let analysisContent = ''

      if (feedback.feedback) {
        analysisContent += `<div class="feedback-section">
                    <h3><span style="color: #FF6B98; font-size: 16px;">💬</span> Nhận xét chi tiết</h3>
                    <p>${feedback.feedback}</p>
                </div>`
      }

      if (
        feedback.recommendations &&
        Array.isArray(feedback.recommendations) &&
        feedback.recommendations.length > 0
      ) {
        analysisContent += `<div class="feedback-section">
                    <h3><span style="color: #FF6B98; font-size: 16px;">✨</span> Đề xuất</h3>
                    <ul>`

        feedback.recommendations.forEach((recommendation) => {
          analysisContent += `<li>${recommendation}</li>`
        })

        analysisContent += `</ul></div>`
      }

      if (feedback.overall_score !== undefined) {
        const score = feedback.overall_score
        const stars = '★'.repeat(Math.min(score, 10))
        const emptyStars = '☆'.repeat(10 - Math.min(score, 10))

        analysisContent += `<div class="feedback-section">
                    <h3><span style="color: #FF6B98; font-size: 16px;">💯</span> Điểm đánh giá</h3>
                    <p style="font-size: 18px;">${stars}${emptyStars} (${score}/10)</p>
                </div>`
      }

      // If we have no structured content but have error information
      if (analysisContent === '' && feedback.error) {
        analysisContent = `<div class="feedback-section">
                    <h3><span style="color: #FF6B98; font-size: 16px;">⚠️</span> Lỗi</h3>
                    <p>${feedback.error}</p>
                    ${
                      feedback.details
                        ? `<p>Chi tiết: ${feedback.details}</p>`
                        : ''
                    }
                </div>`
      }

      // If we still have no content, show the raw JSON
      if (analysisContent === '') {
        analysisContent = `<div class="feedback-section">
                    <pre>${JSON.stringify(feedback, null, 2)}</pre>
                </div>`
      }

      document.querySelector('.analysis-content').innerHTML = analysisContent
    }
  } catch (error) {
    console.error('Error getting fashion feedback:', error)
    document.querySelector('.analysis-content').innerHTML = `
            <div style="padding: 15px; color: #666;">
                <p><i class="fas fa-exclamation-circle"></i> Could not retrieve fashion analysis: ${error.message}</p>
                <p>Enjoy your virtual try-on image!</p>
            </div>
        `
  } finally {
    isGenerating = false
    generateButton.disabled = false
    generateButton.innerHTML =
      '<i class="fas fa-wand-magic-sparkles"></i> Create Magic!'
  }
}

// Add toast styles if not already present
if (!document.getElementById('toast-styles')) {
  const toastStyles = document.createElement('style')
  toastStyles.id = 'toast-styles'
  toastStyles.textContent = `
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background-color: rgba(255, 107, 152, 0.9);
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            transform: translateY(-20px);
            opacity: 0;
            transition: transform 0.3s ease, opacity 0.3s ease;
        }
        
        .toast-error {
            background-color: rgba(255, 70, 70, 0.9);
        }
        
        .toast-success {
            background-color: rgba(70, 200, 120, 0.9);
        }
        
        .feedback-section {
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #FFD6E6;
        }
        
        .feedback-section:last-child {
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }
    `
  document.head.appendChild(toastStyles)
}

window.addEventListener('load', () => {
  const savedPerson = localStorage.getItem('personImageUrl')
  const savedGarment = localStorage.getItem('garmentImageUrl')
  const savedGenerated = localStorage.getItem('generatedImageUrl')

  if (savedPerson) {
    personImage = savedPerson
    // We don't have the File object on reload, so disable generation until new files are selected
    personFile = null
    displayUploadedImage(personDropzone, personInput, savedPerson)
  }

  if (savedGarment) {
    garmentImage = savedGarment
    garmentFile = null
    displayUploadedImage(garmentDropzone, garmentInput, savedGarment)
  }

  if (savedGenerated) {
    const img = document.createElement('img')
    img.src = savedGenerated
    img.className = 'generated-image'
    generatedImageContainer.innerHTML = ''
    generatedImageContainer.appendChild(img)
  }

  // Update button state on load
  checkEnableGenerate()
})
