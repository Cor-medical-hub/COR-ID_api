document.addEventListener("DOMContentLoaded", (event) => {
    const pad=n=>n.toString().padStart(2,'0');

    if(document.getElementById('todayMeta')){
        document.getElementById('todayMeta').textContent=`${pad(new Date().getDate())}.${pad(new Date().getMonth()+1)}.${new Date().getFullYear()}`;
    }


    const uploadBox = document.getElementById('uploadBox');
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    let uploadedFiles = []
    let currentReferralId = null

    const initUploadArea = () => {
        uploadArea.innerHTML = (
            `<div class="upload-box" id="uploadBox" tabindex="0">
                <div class="upload-icon">
                    <svg viewBox="0 0 24 24"><path d="M12 4v10M7 9l5-5 5 5"/><rect x="4" y="18" width="16" height="2" rx="1"/></svg>
                </div>
                <span>Drag your files here<br><b>or scan</b></span>
                <small class="note">up to 5 filesдо</small>
                <input type="file" id="fileInput" multiple accept="image/*,.pdf" hidden>
            </div>`
        )
    }
    const closeModal  = () => {
        uploadedFiles = []
        currentReferralId = null
        document.querySelector('#caseDirection').classList.remove('open')
    }
    const sendFileRequest = async (file) => {
        const formGroup = new FormData()
        formGroup.append('file', file)

        return fetch(`${API_BASE_URL}/api/cases/${currentReferralId}/attachments`, {
            method: "POST",
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
            },
            body: formGroup
        })
            .then(res => res.json())
            .then(() => true)
            .catch(() => false)
    }
    const drawForm = ( formData ) => {
        const formDrawData = [
            {
                label: "Case's type",
                field: "research_type",
                required: true,
                elementType: "select",
                placeholder: "Choose a type",
                selectData: [
                    {
                        id: "патогистология",
                        label: "Pathology"
                    },
                    {
                        id: "иммуногистохимия",
                        label: "Immunohistochemistry"
                    },
                    {
                        id: "цитология",
                        label: "Cytology"
                    },
                    {
                        id: "FISH/CISH",
                        label: "NGS"
                    },
                    {
                        id: "Інше",
                        label: "Other"
                    },
                ]
            },
            {
                label: "Number of containers",
                field: "container_count",
                required: true,
                elementType: "input",
                type: "number",
                placeholder: "0",
            },
            {
                label: "Date of biomaterial collection",
                field: "biomaterial_date",
                elementType: "input",
                type: "date",
            },
            {
                label: "Medical card №",
                field: "medical_card_number",
                elementType: "input",
                type: "text",
                placeholder: "",
            },
            {
                label: "Clinical data",
                field: "clinical_data",
                elementType: "textarea",
            },
            {
                label: "Clinical diagnosis",
                field: "clinical_diagnosis",
                elementType: "input",
                type: "text",
                placeholder: "",
            },
            {
                label: "Medical facility",
                field: "medical_institution",
                elementType: "select",
                placeholder: "Choose a medical facility",
                selectData: [
                    {
                        id: "Феофанія",
                        label: "Феофанія"
                    },
                    {
                        id: "Інститут раку",
                        label: "Cancer Institute"
                    },
                ]
            },
            {
                label: "Department",
                field: "department",
                elementType: "select",
                placeholder: "Choose a branch",
                selectData: [
                    {
                        id: "Хірургія",
                        label: "Surgery"
                    },
                    {
                        id: "Терапія",
                        label: "Therapy"
                    },
                ]
            },
            {
                label: "Attending physician Full name",
                field: "attending_doctor",
                elementType: "input",
                type: "text",
                placeholder: "",
            },
            {
                label: "Doctor's contacts",
                field: "doctor_contacts",
                elementType: "input",
                type: "text",
                placeholder: "+380"
            },
            {
                label: "Medical procedure/surgery",
                field: "medical_procedure",
                elementType: "input",
                type: "text",
                placeholder: ""
            },
        ]
        const formWrapper = document.querySelector("#caseDirection .directorModalLeft")
        formWrapper.innerHTML = ""

        const formNODE = document.createElement('form')
        formNODE.setAttribute("id", "directionForm")

        formDrawData.forEach( data => {
            const formDataField = formData[data.field]

            if(data.elementType === "select"){
                const selectData = data.selectData.reduce((selectDataString, data) => {
                    return selectDataString + (
                        `<li data-v="${data.id}" class="${data.id === formDataField ? "selected" : ""}">
                            ${data.label}
                        </li>`
                    )
                }, '');
                const defaultDataLabel = !formDataField ? "" : data.selectData.find(data => data.id === formDataField)?.label

                formNODE.innerHTML += `
                <div class="directorModalFormGroup ${data.required ? "required" : ""}">
                    <label htmlFor="${data.field}">${data.label} ${data.required ? '<span class="req">*</span>' : ''}</label>
                    <div class="directorModalFormGroup-select">
                        <div class="directorModalFormGroup-input input-box">
                            <span class="label" style="color: ${ formDataField ? "#23155b" : "#a9a4c6"}">${defaultDataLabel || data.placeholder}</span>
                        </div>
                        <ul class="directorModalFormGroup-list">
                            <li class="disabled">${data.placeholder}</li>
                            ${selectData}
                        </ul>
                        <input type="hidden" id="${data.field}" value="${formDataField || ""}" name="${data.field}" ${data.required ? "required" : ""}>
                    </div>
                </div>
                `
                return;
            }
            if(data.elementType === "input"){
                formNODE.innerHTML += `
                <div class="directorModalFormGroup ${data.required ? "required" : ""}">
                    <label htmlFor="container_count">${data.label} ${data.required ? '<span class="req">*</span>' : ''}</label>
                    <input id="${data.field}" value="${formDataField || data.defaultValue || ""}" type="${data.type}" name="${data.field}" class="input input-box ${data.required ? 'required' : ''}" placeholder="${data.placeholder || ""}"
                           min="1">
                </div>
                `
            }
            if(data.elementType === "textarea"){
                formNODE.innerHTML += `
                <div class="directorModalFormGroup ${data.required ? "required" : ""}">
                    <label htmlFor="clinical_data">${data.label}  ${data.required ? '<span class="req">*</span>' : ''}</label>
                    <textarea id="${data.field}" name="${data.field}" placeholder="${data.placeholder || ""}" class="input input-box">${(formDataField || data.defaultValue || "").trim()}</textarea>
                </div>
                `
            }
        })

        formWrapper.append(formNODE)
    }
    const selectPicker = () => {
        document.querySelectorAll('.directorModalFormGroup-select').forEach(select =>{
            const box = select.querySelector('.directorModalFormGroup-input');
            const label = select.querySelector('.label');
            const list = select.querySelector('.directorModalFormGroup-list');
            const input = select.querySelector('input');
            box.onclick=()=> select.classList.toggle('open');

            list.addEventListener('click', e=>{
                const li = e.target.closest('li');
                if(!li || li.classList.contains('disabled')){
                    return;
                }

                list.querySelectorAll('li').forEach( li => li.classList.remove('selected'));
                li.classList.add('selected');

                label.textContent= li.textContent;
                label.style.color='#23155b';

                input.value = li.dataset.v || '';
                select.classList.remove('open');
                box.classList.remove('error');
            });
        });
    }
    const closeSelectPickerByClickingOutside = () => {
        document.addEventListener('click',e=>{
            document.querySelectorAll('.directorModalFormGroup-select.open').forEach( select => {
                if(!select.contains(e.target)) {
                    select.classList.remove('open')
                }
            });
        });
    }
    const showFiles = files => {
        if(!files.length) {
            return;
        }

        const cutTo5Files = [...files].slice(0,5);
        uploadArea.innerHTML = ""

        if(uploadBox.parentElement) {
            uploadBox.remove()
        }

        cutTo5Files.forEach((file)=>{
            const fileViewerWrapperNODE = document.createElement('div');
            fileViewerWrapperNODE.className='thumb';

            if(cutTo5Files.length === 1){
                fileViewerWrapperNODE.classList.add('full')
            }


            const isPDF = file?.content_type?.includes('pdf') || file?.type?.includes('pdf');
            const imgNODE = document.createElement('img');

            if(file.file_url){
                fetch(`${API_BASE_URL}/api${file.file_url}`, {
                    method: "GET",
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    },
                })
                    .then(response => response.blob())
                    .then(blob => {
                        if(isPDF){
                            fileViewerWrapperNODE.innerHTML += `
                            <div style="background: white; height: 100%; width: 100%">
                                <embed
                                    src="${URL.createObjectURL(blob)}#toolbar=0"
                                    type="application/pdf"
                                    style="border: none; background: white; margin: 0 auto; display: block; height: 100%; width: 100%;"
                                ></embed>
                            </div>
                            `
                            uploadArea.appendChild(fileViewerWrapperNODE);
                            return;
                        }

                        imgNODE.src = URL.createObjectURL(blob);
                        imgNODE.onload=()=> URL.revokeObjectURL(imgNODE.src);
                        fileViewerWrapperNODE.appendChild(imgNODE);
                        uploadArea.appendChild(fileViewerWrapperNODE);
                    })
                return;
            }

            if(isPDF){
                fileViewerWrapperNODE.innerHTML += `
                            <div style="background: white; height: 100%; width: 100%">
                                <embed
                                    src="${URL.createObjectURL(file)}#toolbar=0"
                                    type="application/pdf"
                                    style="border: none; background: white; margin: 0 auto; display: block; height: 100%; width: 100%;"
                                ></embed>
                            </div>
                            `
                uploadArea.appendChild(fileViewerWrapperNODE);
                return;
            }


            imgNODE.src=URL.createObjectURL(file);
            imgNODE.onload=()=> URL.revokeObjectURL(imgNODE.src);
            fileViewerWrapperNODE.appendChild(imgNODE);
            uploadArea.appendChild(fileViewerWrapperNODE);
        });
    }
    const submitCaseDirection = (e) => {
        document.querySelector('#caseDirectionSubmit')?.addEventListener('click', (e) => {
            e.preventDefault(e);
            let ok= true;

            document.querySelectorAll('.directorModalFormGroup.required').forEach( box =>{
                if(!box.querySelector('input').value){
                    box.querySelector('.input-box').classList.add('error');
                    ok = false;
                }
            });

            if(ok) {
                const formNODE = document.querySelector('#directionForm');
                const formData = Object.fromEntries(new FormData(formNODE).entries());

                fetch(`${API_BASE_URL}/api/cases/referrals/upsert`, {
                    method: "POST",
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        case_id: cases[lastActiveCaseIndex].id,
                        ...formData,
                        biomaterial_date: formData.biomaterial_date || null
                    })
                })
                    .then(res => res.json())
                    .then((referralData) => {
                        if(!referralData.id){
                            return showErrorAlert('Щось пішло не так');
                        }
                        currentReferralId = referralData.id;

                        if(uploadedFiles.length){
                            Promise.all([...uploadedFiles].map(sendFileRequest))
                                .then(res => {
                                    showSuccessAlert('Форму збережено!')


                                    closeModal()
                                })

                            return;
                        }

                        showSuccessAlert('Форму збережено!')
                        closeModal()
                    })
                    .catch((e) => {
                        showErrorAlert(e?.message || "Щось пішло не так")
                    })
            }
            else {
                showErrorAlert('Заповніть обов"язкові поля!')
            }
        })

    }
    const dropBoxEventsHandler = () => {
        uploadBox?.addEventListener('click', () => {
            fileInput.click()
        });
        uploadBox?.addEventListener('dragover', e => {
            e.preventDefault();
            uploadBox.classList.add('hover');
        });
        uploadBox?.addEventListener('dragenter', e => {
            e.preventDefault();
            uploadBox.classList.add('hover');
        });
        uploadBox?.addEventListener('dragleave', e => {
            e.preventDefault();
            uploadBox.classList.remove('hover');
        });
        uploadBox?.addEventListener('drop', e => {
            e.preventDefault();
            uploadBox.classList.remove('hover');
            showFiles(e.dataTransfer.files)
            uploadedFiles = [...uploadedFiles, ...e.dataTransfer.files]
        });
        fileInput?.addEventListener('change',e => {
            showFiles(e.target.files)
            uploadedFiles = [...uploadedFiles, ...e.target.files]
        });
    }
    const openDirectionModal = () => {
        document.querySelector('#directionModalBtn')?.addEventListener('click', e => {
            uploadedFiles = []
            currentReferralId = null
            document.querySelector('#caseDirection').classList.add('open')
            fetch(`${API_BASE_URL}/api/cases/referrals/${cases[lastActiveCaseIndex].id}`, {
                method: "GET",
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                    "Content-Type": "application/json"
                },
            })
                .then(res => {
                    if(res.status === 404){
                        return {}
                    }

                    return res.json()
                })
                .then(refferalData => {
                    currentReferralId = refferalData.id
                    drawForm( refferalData )
                    selectPicker();
                    closeSelectPickerByClickingOutside();
                    showFiles(refferalData.attachments || [])
                })
        })
    }

    submitCaseDirection();
    dropBoxEventsHandler();
    openDirectionModal();
})
