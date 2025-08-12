// 도메인 상세 페이지 실시간 업데이트 기능

let lastUpdateTime = new Date();

function getStatusColor(status) {
    switch(status) {
        case 'GREEN': return 'bg-green-500';
        case 'AMBER': return 'bg-yellow-500';
        case 'RED': return 'bg-red-500';
        default: return 'bg-gray-500';
    }
}

function getStatusText(status, latest_check) {
    if (status === 'GREEN' && latest_check && latest_check.latency_ms) {
        return `정상 (${latest_check.latency_ms}ms)`;
    } else if (status === 'RED' && latest_check) {
        return `오류 (${latest_check.status_code || '연결실패'})`;
    } else if (status === 'AMBER') {
        return '신호없음';
    }
    return '알 수 없음';
}

function getStatusTextColor(status) {
    switch(status) {
        case 'GREEN': return 'text-green-600';
        case 'AMBER': return 'text-yellow-600';
        case 'RED': return 'text-red-600';
        default: return 'text-gray-600';
    }
}

function formatDateTime(isoString) {
    if (!isoString) return '체크된 적 없음';
    
    const date = new Date(isoString);
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const hour = date.getHours();
    const minute = date.getMinutes();
    
    return `${month}월 ${day}일 ${hour}:${minute.toString().padStart(2, '0')}`;
}

function refreshDomainDetail() {
    updateDomainDetail();
}

function updateDomainDetail() {
    const domainId = window.DOMAIN_ID; // 템플릿에서 설정될 변수
    
    fetch(`/dashboard/api/domain/${domainId}/detail/`)
        .then(response => response.json())
        .then(data => {
            data.endpoint_status.forEach(endpoint => {
                const endpointItem = document.querySelector(`[data-endpoint-id="${endpoint.endpoint_id}"]`);
                if (endpointItem) {
                    // 상태 아이콘 업데이트
                    const statusIcon = endpointItem.querySelector('.status-icon');
                    if (statusIcon) {
                        statusIcon.className = `w-4 h-4 rounded-full status-icon ${getStatusColor(endpoint.status)}`;
                    }
                    
                    // 상태 결과 업데이트
                    const statusResult = endpointItem.querySelector('.status-result');
                    if (statusResult) {
                        statusResult.className = `text-sm font-medium status-result ${getStatusTextColor(endpoint.status)}`;
                        statusResult.textContent = getStatusText(endpoint.status, endpoint.latest_check);
                    }
                    
                    // 마지막 체크 시간 업데이트
                    const lastChecked = endpointItem.querySelector('.last-checked');
                    if (lastChecked) {
                        lastChecked.textContent = endpoint.latest_check ? 
                            formatDateTime(endpoint.latest_check.checked_at) : 
                            '체크된 적 없음';
                    }
                }
            });
            
            lastUpdateTime = new Date(data.last_updated);
        })
        .catch(error => {
            console.error('Domain detail update failed:', error);
        });
}

// 자동 새로고침 (30초마다)
setInterval(updateDomainDetail, 30000);

// 페이지 로드 시 초기 업데이트
document.addEventListener('DOMContentLoaded', function() {
    // 5초 후 첫 번째 자동 업데이트
    setTimeout(updateDomainDetail, 5000);
});
