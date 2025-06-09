document.addEventListener("DOMContentLoaded", (event) => {
    const pad=n=>n.toString().padStart(2,'0');
    document.getElementById('todayMeta').textContent=`${pad(new Date().getDate())}.${pad(new Date().getMonth()+1)}.${new Date().getFullYear()}`;


    const uploadBox = document.getElementById('uploadBox');
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

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
        uploadArea.querySelectorAll('.thumb').forEach(thumb => thumb.remove());

        if(uploadBox.parentElement) {
            uploadBox.remove()
        }

        cutTo5Files.forEach((file)=>{
            const fileViewerWrapperNODE = document.createElement('div');
            fileViewerWrapperNODE.className='thumb';

            if(cutTo5Files.length === 1){
                fileViewerWrapperNODE.classList.add('full')
            }

            const imgNODE = document.createElement('img');
            imgNODE.src=URL.createObjectURL(file);
            imgNODE.onload=()=> URL.revokeObjectURL(imgNODE.src);
            fileViewerWrapperNODE.appendChild(imgNODE);
            uploadArea.appendChild(fileViewerWrapperNODE);
        });
    }
    const submitCaseDirection = (e) => {
        document.querySelector('#caseDirectionSubmit').addEventListener('click', (e) => {
            e.preventDefault(e);
            let ok= true;

            document.querySelectorAll('.required .directorModalFormGroup-input').forEach( box =>{
                if(!box.parentElement.querySelector('input').value){
                    box.classList.add('error');
                    ok = false;
                }
            });

            if(ok) {
                const formNODE = document.querySelector('#directionForm');
                const formData = Object.fromEntries(new FormData(formNODE).entries());
                console.log(formData, "object")
                fetch(`${API_BASE_URL}/api/cases/referrals/upsert`, {
                    method: "POST",
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        case_id: "d9a1028e-4ff4-4336-875f-07d31440063b",
                        ...formData,

                    })
                })
                    .then(res => res.json())
                    .then(() => {
                        alert('Форму збережено!')
                    })
            }
        })

        }
    const dropBoxEventsHandler = () => {
        uploadBox.addEventListener('click', () => {
            fileInput.click()
        });
        uploadBox.addEventListener('dragover', e => {
            e.preventDefault();
            uploadBox.classList.add('hover');
        });
        uploadBox.addEventListener('dragenter', e => {
            e.preventDefault();
            uploadBox.classList.add('hover');
        });
        uploadBox.addEventListener('dragleave', e => {
            e.preventDefault();
            uploadBox.classList.remove('hover');
        });
        uploadBox.addEventListener('drop', e => {
            e.preventDefault();
            uploadBox.classList.remove('hover');
            showFiles(e.dataTransfer.files)
        });
        fileInput.addEventListener('change',e => {
            showFiles(e.target.files)
        });
    }

    selectPicker();
    closeSelectPickerByClickingOutside();
    submitCaseDirection();
    dropBoxEventsHandler();
})
