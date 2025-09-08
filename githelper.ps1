<#
.SYNOPSIS
Git操作快捷助手 - 简化当前目录Git仓库的常用操作

.DESCRIPTION
提供一系列快捷命令，简化Git仓库的日常操作，如状态查看、提交、拉取、推送等
自动定位到脚本所在目录进行操作

.NOTES
作者: 豆包编程助手
版本: 1.1
#>

# 定位到脚本所在目录
$scriptPath = $PSScriptRoot
Write-Host "正在切换到脚本所在目录: $scriptPath" -ForegroundColor Yellow
Set-Location $scriptPath

# 检查是否在Git仓库中
function Test-GitRepository {
    if (-not (Test-Path .git)) {
        Write-Host "错误: 当前目录不是Git仓库" -ForegroundColor Red
        return $false
    }
    return $true
}

# 显示Git状态
function Invoke-GitStatus {
    if (-not (Test-GitRepository)) { return }
    Write-Host "`n=== Git 状态 ===" -ForegroundColor Cyan
    git status
}

# 显示Git日志
function Invoke-GitLog {
    if (-not (Test-GitRepository)) { return }
    Write-Host "`n=== Git 日志 ===" -ForegroundColor Cyan
    git log --oneline --graph --decorate
}

# 添加所有更改
function Invoke-GitAddAll {
    if (-not (Test-GitRepository)) { return }
    Write-Host "`n=== 添加所有更改 ===" -ForegroundColor Cyan
    git add .
    Write-Host "已添加所有更改" -ForegroundColor Green
}

# 提交更改
function Invoke-GitCommit {
    if (-not (Test-GitRepository)) { return }
    
    $message = Read-Host "请输入提交信息"
    if ([string]::IsNullOrWhiteSpace($message)) {
        Write-Host "错误: 提交信息不能为空" -ForegroundColor Red
        return
    }
    
    Write-Host "`n=== 提交更改 ===" -ForegroundColor Cyan
    git commit -m $message
}

# 拉取远程更改
function Invoke-GitPull {
    if (-not (Test-GitRepository)) { return }
    Write-Host "`n=== 拉取远程更改 ===" -ForegroundColor Cyan
    git pull
}

# 推送本地更改
function Invoke-GitPush {
    if (-not (Test-GitRepository)) { return }
    Write-Host "`n=== 推送本地更改 ===" -ForegroundColor Cyan
    git push
}

# 显示分支信息
function Invoke-GitBranches {
    if (-not (Test-GitRepository)) { return }
    Write-Host "`n=== 分支信息 ===" -ForegroundColor Cyan
    git branch -v
}

# 切换分支
function Invoke-GitCheckout {
    if (-not (Test-GitRepository)) { return }
    
    $branch = Read-Host "请输入要切换的分支名称"
    if ([string]::IsNullOrWhiteSpace($branch)) {
        Write-Host "错误: 分支名称不能为空" -ForegroundColor Red
        return
    }
    
    Write-Host "`n=== 切换到分支 $branch ===" -ForegroundColor Cyan
    git checkout $branch
}

# 创建新分支
function Invoke-GitNewBranch {
    if (-not (Test-GitRepository)) { return }
    
    $branch = Read-Host "请输入新分支名称"
    if ([string]::IsNullOrWhiteSpace($branch)) {
        Write-Host "错误: 分支名称不能为空" -ForegroundColor Red
        return
    }
    
    Write-Host "`n=== 创建并切换到新分支 $branch ===" -ForegroundColor Cyan
    git checkout -b $branch
}

# 主菜单
function Show-Menu {
    Clear-Host
    Write-Host "================ Git 快捷助手 ================" -ForegroundColor Green
    Write-Host "当前操作目录: $(Get-Location)" -ForegroundColor Yellow
    Write-Host "1. 查看状态 (git status)"
    Write-Host "2. 查看日志 (git log)"
    Write-Host "3. 添加所有更改 (git add .)"
    Write-Host "4. 提交更改 (git commit -m)"
    Write-Host "5. 拉取远程 (git pull)"
    Write-Host "6. 推送本地 (git push)"
    Write-Host "7. 查看分支 (git branch)"
    Write-Host "8. 切换分支 (git checkout)"
    Write-Host "9. 创建新分支 (git checkout -b)"
    Write-Host "Q. 退出"
    Write-Host "==============================================" -ForegroundColor Green
}

# 主程序
do {
    Show-Menu
    $choice = Read-Host "请选择操作 (1-9, Q退出)"
    
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
        'Q' { Write-Host "退出程序..." -ForegroundColor Green }
        default { Write-Host "无效选择，请重试" -ForegroundColor Red }
    }
    
    if ($choice -ne 'Q') {
        Read-Host "`n按Enter键继续..."
    }
} while ($choice -ne 'Q')
    