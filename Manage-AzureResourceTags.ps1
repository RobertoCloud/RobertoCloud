#Requires -Modules Az.Accounts, Az.Resources
<#
.SYNOPSIS
    Manages Azure resource tags by identifying resources missing specific tags
    ('customer', 'environment', 'project') and updating them from their resource group.
.DESCRIPTION
    This script connects to Azure, fetches all resources in the current subscription,
    checks for missing 'customer', 'environment', or 'project' tags on each resource.
    If tags are missing, it attempts to find them on the resource's parent resource group.
    The script then presents these proposed changes in batches for user confirmation
    before applying the tags using Update-AzTag.
.NOTES
    Version: 1.0
    Author: AI Assistant
    Prerequisites: Azure Az.Accounts and Az.Resources PowerShell modules.
                   User must have permissions to read resources, resource groups, and update tags.
#>

# Script Start Logging
Write-Host "--------------------------------------------------------------------"
Write-Host "Starting Script: Manage-AzureResourceTags.ps1"
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "--------------------------------------------------------------------`n"

# --- Configuration ---
# Define the tags to check and inherit
$requiredTags = @('customer', 'environment', 'project')
$batchSize = 5 # Number of resources to process in each confirmation batch
$logTimeFormat = 'yyyy-MM-dd HH:mm:ss'

# --- Function for Logging ---
function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO" # INFO, WARNING, ERROR
    )
    $timestamp = Get-Date -Format $logTimeFormat
    $formattedMessage = "$timestamp [$Level] - $Message"
    Write-Host $formattedMessage
    if ($Level -eq "ERROR" -or $Level -eq "WARNING") {
        # Potentially log to a file here in future enhancements
    }
}

# --- 1. Connect to Azure ---
try {
    Write-Log "Attempting to connect to Azure..."
    Connect-AzAccount -ErrorAction Stop
    $currentContext = Get-AzContext
    Write-Log "Successfully connected to Azure."
    Write-Log "Subscription: $($currentContext.Subscription.Name) (ID: $($currentContext.Subscription.Id))"
    Write-Log "Tenant: $($currentContext.Tenant.Id)"
    Write-Log "Account: $($currentContext.Account.Id)"
}
catch {
    Write-Log "Failed to connect to Azure. Please ensure the Az.Accounts module is installed, you are logged in, and have appropriate permissions." -Level "ERROR"
    Write-Log "Error Details: $($_.Exception.Message)" -Level "ERROR"
    Write-Host "`n--------------------------------------------------------------------"
    Write-Host "Script Aborted Due to Connection Error."
    Write-Host "--------------------------------------------------------------------"
    exit 1
}

# --- 2. Fetch Azure Resources ---
$allResources = @()
try {
    Write-Log "Fetching all resources from the current subscription '$($currentContext.Subscription.Name)'..."
    $allResources = Get-AzResource -ErrorAction Stop
    Write-Log "Successfully fetched $($allResources.Count) resources."
}
catch {
    Write-Log "Failed to fetch Azure resources." -Level "ERROR"
    Write-Log "Error Details: $($_.Exception.Message)" -Level "ERROR"
    Write-Host "`n--------------------------------------------------------------------"
    Write-Host "Script Aborted Due to Resource Fetching Error."
    Write-Host "--------------------------------------------------------------------"
    exit 1
}

if ($allResources.Count -eq 0) {
    Write-Log "No resources found in the current subscription. Exiting script."
    Write-Host "`n--------------------------------------------------------------------"
    Write-Host "Script Finished."
    Write-Host "--------------------------------------------------------------------"
    exit 0
}

# --- 3. Identify Resources Needing Tag Updates ---
$resourcesToUpdateCalculation = [System.Collections.Generic.List[PSCustomObject]]::new()
Write-Log "Checking all $($allResources.Count) resources for missing or empty tags: $($requiredTags -join ', ')"
foreach ($resourceItem in $allResources) {
    $missingOrEmptyTagsOnResource = @{}
    $currentResourceTags = if ($null -ne $resourceItem.Tags) { $resourceItem.Tags } else { @{} }

    foreach ($tagName in $requiredTags) {
        if (-not $currentResourceTags.ContainsKey($tagName) -or [string]::IsNullOrWhiteSpace($currentResourceTags[$tagName])) {
            $missingOrEmptyTagsOnResource[$tagName] = $null # Mark as missing or empty
        }
    }

    if ($missingOrEmptyTagsOnResource.Count -gt 0) {
        Write-Log "Resource '$($resourceItem.Name)' (Type: $($resourceItem.ResourceType)) is missing/has empty value for tags: $($missingOrEmptyTagsOnResource.Keys -join ', ')."
        try {
            $resourceGroupName = $resourceItem.ResourceGroupName
            $rg = Get-AzResourceGroup -Name $resourceGroupName -ErrorAction Stop
            $rgTags = if ($null -ne $rg.Tags) { $rg.Tags } else { @{} }

            $tagsToInheritFromRG = @{}
            $logDetailsForThisResource = @()

            foreach ($tagName in $missingOrEmptyTagsOnResource.Keys) {
                if ($rgTags.ContainsKey($tagName) -and -not [string]::IsNullOrWhiteSpace($rgTags[$tagName])) {
                    $tagsToInheritFromRG[$tagName] = $rgTags[$tagName]
                    $logDetailsForThisResource += "    - Tag '$tagName' will be updated/added with value '$($rgTags[$tagName])' from RG '$resourceGroupName'."
                } else {
                    $logDetailsForThisResource += "    - Tag '$tagName' is also missing, empty, or not found in RG '$resourceGroupName'."
                }
            }

            if ($tagsToInheritFromRG.Count -gt 0) {
                $resourcesToUpdateCalculation.Add([PSCustomObject]@{
                    Resource            = $resourceItem
                    TagsToApply         = $tagsToInheritFromRG
                    OriginalMissingKeys = $missingOrEmptyTagsOnResource.Keys
                    InheritedLogDetails = $logDetailsForThisResource
                })
                Write-Log "Resource '$($resourceItem.Name)' added to update list. Will inherit: $($tagsToInheritFromRG.Keys -join ', ')."
            } else {
                Write-Log "Resource '$($resourceItem.Name)' had missing tags, but no corresponding valid tags found in RG '$resourceGroupName'." -Level "WARNING"
            }
        }
        catch {
            Write-Log "Failed to get RG '$($resourceItem.ResourceGroupName)' for resource '$($resourceItem.Name)' or process its tags." -Level "ERROR"
            Write-Log "Error Details: $($_.Exception.Message)" -Level "ERROR"
        }
    }
}
Write-Log "Finished checking resources. $($resourcesToUpdateCalculation.Count) resource(s) identified for potential tag updates."

# --- 4. Batched Confirmation and Tag Application ---
$processedResourcesForActualTagging = [System.Collections.Generic.List[PSCustomObject]]::new()
$userInterruptedQuit = $false

if ($resourcesToUpdateCalculation.Count -gt 0) {
    Write-Log "`nStarting batched confirmation for $($resourcesToUpdateCalculation.Count) resource(s)." -Level "INFO"

    for ($i = 0; $i -lt $resourcesToUpdateCalculation.Count; $i += $batchSize) {
        if ($userInterruptedQuit) { break }

        $currentBatch = $resourcesToUpdateCalculation[$i..[System.Math]::Min($i + $batchSize - 1, $resourcesToUpdateCalculation.Count - 1)]
        $batchNumber = ($i / $batchSize) + 1
        $totalBatches = [System.Math]::Ceiling($resourcesToUpdateCalculation.Count / $batchSize)

        Write-Host "`n--------------------------------------------------------------------"
        Write-Log "Displaying Batch $batchNumber of $totalBatches"
        Write-Host "--------------------------------------------------------------------`n"

        foreach ($itemInBatch in $currentBatch) {
            Write-Log "Resource Name : $($itemInBatch.Resource.Name) (RG: $($itemInBatch.Resource.ResourceGroupName), Type: $($itemInBatch.Resource.ResourceType))" -Level "INFO"
            Write-Host "  Proposed changes:"

            $updatableTagsExistInItem = $false
            foreach($detail in $itemInBatch.InheritedLogDetails) {
                if ($detail -match "will be updated/added") { # Check if it's a positive update
                    Write-Host $detail
                    $updatableTagsExistInItem = $true
                }
            }
            if (-not $updatableTagsExistInItem) {
                Write-Host "    - No tags will be updated/added from RG for this resource (either not found in RG or RG tag was empty/missing)."
            }

            $nonInheritableTags = $itemInBatch.OriginalMissingKeys | Where-Object { -not $itemInBatch.TagsToApply.ContainsKey($_) }
            if ($nonInheritableTags.Count -gt 0) {
                Write-Host "  The following originally missing/empty tags were NOT found in the RG (or RG tag was empty) and will NOT be updated:"
                $nonInheritableTags | ForEach-Object { Write-Host "    - $_" }
            }
            Write-Host # Blank line for readability
        }
        Write-Host "--------------------------------------------------------------------"

        $validResponse = $false
        while (-not $validResponse) {
            $choice = Read-Host "Process Batch $batchNumber? (Yes/No/Skip to next batch/Quit script) [Y/N/S/Q]"
            switch ($choice.ToUpper()) {
                'Y' { Write-Log "User chose YES for batch $batchNumber."; $processedResourcesForActualTagging.AddRange($currentBatch); $validResponse = $true }
                'N' { Write-Log "User chose NO for batch $batchNumber. Skipping these resources."; $validResponse = $true }
                'S' { Write-Log "User chose SKIP for batch $batchNumber. Moving to next batch."; $validResponse = $true; break }
                'Q' { Write-Log "User chose QUIT during batch $batchNumber. Halting further processing."; $userInterruptedQuit = $true; $validResponse = $true }
                default { Write-Log "Invalid input. Please enter Y, N, S, or Q." -Level "WARNING" }
            }
        }
    } # End of batch loop

    if ($processedResourcesForActualTagging.Count -gt 0) {
        Write-Log "`nUser has confirmed $($processedResourcesForActualTagging.Count) resource(s) for tag updates. Applying tags now..." -Level "INFO"
        Write-Host "--------------------------------------------------------------------`n"
        $successfullyUpdatedCount = 0
        $failedUpdateCount = 0

        foreach ($itemToApplyTagsTo in $processedResourcesForActualTagging) {
            $resourceForTagging = $itemToApplyTagsTo.Resource
            $tagsToApplyOnResource = $itemToApplyTagsTo.TagsToApply

            Write-Log "Processing Resource: $($resourceForTagging.Name) (RG: $($resourceForTagging.ResourceGroupName))"

            try {
                # Fetch current tags again before updating to ensure merge is based on latest state
                $currentResourceStateForTagging = Get-AzResource -ResourceId $resourceForTagging.ResourceId -ErrorAction Stop
                $existingTagsOnResource = if ($null -ne $currentResourceStateForTagging.Tags) { $currentResourceStateForTagging.Tags } else { @{} }

                $finalTagsForUpdate = $existingTagsOnResource.Clone()
                foreach ($tagKey in $tagsToApplyOnResource.Keys) {
                    $finalTagsForUpdate[$tagKey] = $tagsToApplyOnResource[$tagKey] # Add or overwrite
                }

                Write-Log "Applying tags to '$($resourceForTagging.Name)'. Final tags: $($finalTagsForUpdate | ConvertTo-Json -Compress -Depth 3)"
                Update-AzTag -ResourceId $resourceForTagging.ResourceId -Tag $finalTagsForUpdate -Operation Merge -ErrorAction Stop
                Write-Log "Successfully applied/updated tags for resource '$($resourceForTagging.Name)'."
                $successfullyUpdatedCount++
            }
            catch {
                Write-Log "Failed to apply tags to resource '$($resourceForTagging.Name)'." -Level "ERROR"
                Write-Log "Error Details: $($_.Exception.Message)" -Level "ERROR"
                Write-Log "Tags that were attempted: $($tagsToApplyOnResource | ConvertTo-Json -Compress -Depth 3)" -Level "ERROR"
                $failedUpdateCount++
            }
            Write-Host # Blank line
        }
        Write-Log "Tagging operations completed for confirmed resources."
        Write-Log "Summary: $successfullyUpdatedCount resource(s) updated successfully, $failedUpdateCount resource(s) failed."
    } elseif ($userInterruptedQuit) {
         Write-Log "Script execution was quit by the user. No tags were applied in the last unprocessed batches." -Level "INFO"
    } else {
        Write-Log "No resources were confirmed by the user for tag updates." -Level "INFO"
    }
}
else {
    Write-Log "No resources found requiring tag updates after initial check." -Level "INFO"
}

Write-Host "`n--------------------------------------------------------------------"
Write-Log "Script Finished."
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "--------------------------------------------------------------------"
