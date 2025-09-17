




function updatePrinterDropdown() {
    const printerInput = document.getElementById('printerIp');
    const datalist = document.getElementById('printerIps');
    if (!printerInput || !datalist) return;

    if (!Array.isArray(availablePrinters)) {
        console.error('availablePrinters не является массивом:', availablePrinters);
        availablePrinters = [];
    }

    const currentValue = printerInput.value;
    datalist.innerHTML = '';
    
    if (availablePrinters.length > 0) {
        availablePrinters.forEach(printer => {
            const option = document.createElement('option');
            option.value = printer.ip_address;
            option.textContent = `${printer.ip_address}${printer.location ? ` (${printer.location})` : ''}`;
            option.dataset.type = printer.device_class;
            datalist.appendChild(option);
        });
    }
    
    if (currentValue) {
        printerInput.value = currentValue;
    }

    // Обработчик изменения выбора принтера
    printerInput.addEventListener('input', function() {
        const selectedOption = Array.from(datalist.options).find(opt => opt.value === this.value);
        const hopperNumberContainer = document.getElementById('hopperNumberContainer');
        const labelText = document.getElementById('labelText');
        const sendButton = document.querySelector('#testModal button[onclick="sendToPrint()"]');

        // Список всех стандартных полей, которые нужно скрывать для StickerPrinter
        const otherFields = [
            'template', 'hopperNumberContainer', 'clinicId', 'caseCode',
            'sampleNumber', 'cassetteNumber', 'glassNumber', 'staining', 'patientCorId', 'sendLabelButton'
        ].map(id => document.getElementById(id) || document.getElementById(id + 'Container'));

        if (selectedOption) {
            const type = selectedOption.dataset.type;
        
            // Сначала скрываем все поля по умолчанию
            labelText.style.display = 'none';
            sendButton.style.display = 'none';
            hopperNumberContainer.style.display = 'none';
            otherFields.forEach(f => f && (f.style.display = 'block')); // по умолчанию все стандартные поля показываем
        
            switch (type) {
                case 'GlassPrinter':
                case 'CassetPrinter':
                    // Принтер стекол и обычный принтер кассет – показываем стандартные поля
                    // Все остальные поля уже отображены, ничего дополнительно не делаем
                    hopperNumberContainer.style.display = 'none';
                    scannerContainer.style.display = 'none';
                    break;
        
                case 'CassetPrinterHopper':
                    // Принтер-хоппер – показываем хоппер
                    scannerContainer.style.display = 'none';
                    hopperNumberContainer.style.display = 'block';
                    break;
        
                case 'StickerPrinter':
                    // Принтер наклеек – показываем textarea и кнопку, скрываем все стандартные поля
                    scannerContainer.style.display = 'none';
                    labelText.style.display = 'block';
                    sendButton.style.display = 'inline-block';
                    otherFields.forEach(f => f && (f.style.display = 'none'));
                    break;

                case 'scanner_docs':
                    // Принтер наклеек – показываем textarea и кнопку, скрываем все стандартные поля
                    scannerContainer.style.display = 'block';
                    sendButton.style.display = 'inline-block';
                    otherFields.forEach(f => f && (f.style.display = 'none'));
                    break;    
        
                // Здесь можно добавить новые типы принтеров с их настройками отображения
                default:
                    // Для неизвестных типов – скрываем textarea и кнопку
                    scannerContainer.style.display = 'none';
                    hopperNumberContainer.style.display = 'none';
                    labelText.style.display = 'none';
                    sendButton.style.display = 'none';
                    otherFields.forEach(f => f && (f.style.display = 'block'));
                   
                    break;
            }
        } else {
            // Если ничего не выбрано, скрываем специфические элементы и показываем стандартные поля
            labelText.style.display = 'none';
            sendButton.style.display = 'none';
            hopperNumberContainer.style.display = 'none';
            otherFields.forEach(f => f && (f.style.display = 'block'));
        }
    });
    
    // Вызываем событие input для обновления состояния при загрузке
    printerInput.dispatchEvent(new Event('input'));
}



