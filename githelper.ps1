<#
.SYNOPSIS
Git����������� - �򻯵�ǰĿ¼Git�ֿ�ĳ��ò���

.DESCRIPTION
�ṩһϵ�п�������Git�ֿ���ճ���������״̬�鿴���ύ����ȡ�����͵�
�Զ���λ���ű�����Ŀ¼���в���

.NOTES
����: �����������
�汾: 1.1
#>

# ��λ���ű�����Ŀ¼
$scriptPath = $PSScriptRoot
Write-Host "�����л����ű�����Ŀ¼: $scriptPath" -ForegroundColor Yellow
Set-Location $scriptPath

# ����Ƿ���Git�ֿ���
function Test-GitRepository {
    if (-not (Test-Path .git)) {
        Write-Host "����: ��ǰĿ¼����Git�ֿ�" -ForegroundColor Red
        return $false
    }
    return $true
}

# ��ʾGit״̬
function Invoke-GitStatus {
    if (-not (Test-GitRepository)) { return }
    Write-Host "`n=== Git ״̬ ===" -ForegroundColor Cyan
    git status
}

# ��ʾGit��־
function Invoke-GitLog {
    if (-not (Test-GitRepository)) { return }
    Write-Host "`n=== Git ��־ ===" -ForegroundColor Cyan
    git log --oneline --graph --decorate
}

# ������и���
function Invoke-GitAddAll {
    if (-not (Test-GitRepository)) { return }
    Write-Host "`n=== ������и��� ===" -ForegroundColor Cyan
    git add .
    Write-Host "��������и���" -ForegroundColor Green
}

# �ύ����
function Invoke-GitCommit {
    if (-not (Test-GitRepository)) { return }
    
    $message = Read-Host "�������ύ��Ϣ"
    if ([string]::IsNullOrWhiteSpace($message)) {
        Write-Host "����: �ύ��Ϣ����Ϊ��" -ForegroundColor Red
        return
    }
    
    Write-Host "`n=== �ύ���� ===" -ForegroundColor Cyan
    git commit -m $message
}

# ��ȡԶ�̸���
function Invoke-GitPull {
    if (-not (Test-GitRepository)) { return }
    Write-Host "`n=== ��ȡԶ�̸��� ===" -ForegroundColor Cyan
    git pull
}

# ���ͱ��ظ���
function Invoke-GitPush {
    if (-not (Test-GitRepository)) { return }
    Write-Host "`n=== ���ͱ��ظ��� ===" -ForegroundColor Cyan
    git push
}

# ��ʾ��֧��Ϣ
function Invoke-GitBranches {
    if (-not (Test-GitRepository)) { return }
    Write-Host "`n=== ��֧��Ϣ ===" -ForegroundColor Cyan
    git branch -v
}

# �л���֧
function Invoke-GitCheckout {
    if (-not (Test-GitRepository)) { return }
    
    $branch = Read-Host "������Ҫ�л��ķ�֧����"
    if ([string]::IsNullOrWhiteSpace($branch)) {
        Write-Host "����: ��֧���Ʋ���Ϊ��" -ForegroundColor Red
        return
    }
    
    Write-Host "`n=== �л�����֧ $branch ===" -ForegroundColor Cyan
    git checkout $branch
}

# �����·�֧
function Invoke-GitNewBranch {
    if (-not (Test-GitRepository)) { return }
    
    $branch = Read-Host "�������·�֧����"
    if ([string]::IsNullOrWhiteSpace($branch)) {
        Write-Host "����: ��֧���Ʋ���Ϊ��" -ForegroundColor Red
        return
    }
    
    Write-Host "`n=== �������л����·�֧ $branch ===" -ForegroundColor Cyan
    git checkout -b $branch
}

# ���˵�
function Show-Menu {
    Clear-Host
    Write-Host "================ Git ������� ================" -ForegroundColor Green
    Write-Host "��ǰ����Ŀ¼: $(Get-Location)" -ForegroundColor Yellow
    Write-Host "1. �鿴״̬ (git status)"
    Write-Host "2. �鿴��־ (git log)"
    Write-Host "3. ������и��� (git add .)"
    Write-Host "4. �ύ���� (git commit -m)"
    Write-Host "5. ��ȡԶ�� (git pull)"
    Write-Host "6. ���ͱ��� (git push)"
    Write-Host "7. �鿴��֧ (git branch)"
    Write-Host "8. �л���֧ (git checkout)"
    Write-Host "9. �����·�֧ (git checkout -b)"
    Write-Host "Q. �˳�"
    Write-Host "==============================================" -ForegroundColor Green
}

# ������
do {
    Show-Menu
    $choice = Read-Host "��ѡ����� (1-9, Q�˳�)"
    
    switch ($choice) {
        '1' { Invoke-GitStatus }
        '2' { Invoke-GitLog }
        '3' { Invoke-GitAddAll }
        '4' { Invoke-GitCommit }
        '5' { Invoke-GitPull }
        '6' { Invoke-GitPush }
        '7' { Invoke-GitBranches }
        '8' { Invoke-GitCheckout }
        '9' { Invoke-GitNewBranch }
        'Q' { Write-Host "�˳�����..." -ForegroundColor Green }
        default { Write-Host "��Чѡ��������" -ForegroundColor Red }
    }
    
    if ($choice -ne 'Q') {
        Read-Host "`n��Enter������..."
    }
} while ($choice -ne 'Q')
    