# HR Dashboard Testing Checklist

## Pre-Testing Verification ✅

### Code Structure
- [x] All methods properly defined in `models/hr_employee.py`
- [x] JavaScript methods properly defined in `hrms_dashboard.js`
- [x] XML template structure correct
- [x] CSS styles added
- [x] No linting errors
- [x] moment.js loaded via CDN in manifest

### Backend Methods
- [x] `get_quick_actions_data()` - Returns attendance, leave, document data
- [x] `get_additional_metrics()` - Returns approvals, documents, loans, insurance, contracts
- [x] `action_attendance_check_in_out()` - Handles attendance action

### Frontend Methods
- [x] `quickActionAttendance()` - Attendance check in/out
- [x] `quickActionLeaveRequest()` - Opens leave request form
- [x] `quickActionDocuments()` - Opens documents view
- [x] `toggleDarkMode()` - Toggles dark mode

## Testing Steps

### 1. Module Installation
```bash
# In Odoo, upgrade the module:
Apps > ent_hrms_dashboard > Upgrade
```

### 2. Quick Actions Testing

#### Test Attendance Button
- [ ] Navigate to HR Dashboard
- [ ] Check if attendance button appears (if hr_attendance installed)
- [ ] Click "Check In" - should mark attendance
- [ ] Button should change to "Check Out"
- [ ] Click "Check Out" - should mark checkout
- [ ] Button should change back to "Check In"

#### Test Leave Request Button
- [ ] Check if leave request button appears
- [ ] Click button - should open leave request form
- [ ] Form should be functional

#### Test Documents Button
- [ ] Check if documents button appears (if ent_employee_documents_expiry installed)
- [ ] If documents expiring, count should be visible
- [ ] Click button - should open documents view

#### Test Dark Mode Toggle
- [ ] Click dark mode toggle button
- [ ] Dashboard should switch to dark theme
- [ ] Refresh page - dark mode preference should persist
- [ ] Click again - should switch back to light theme

### 3. Additional Metrics Testing

#### Test Pending Approvals (HR Manager only)
- [ ] Login as HR Manager
- [ ] Check if pending approvals widget appears
- [ ] Count should show pending leave + expense approvals
- [ ] Widget should only show if there are pending approvals

#### Test Document Expiry Alerts
- [ ] Check if document expiry widget appears (if module installed)
- [ ] Should show count of documents expiring in next 30 days
- [ ] Widget should only show if there are expiring documents

#### Test Loan Status
- [ ] Check if loan widget appears (if ent_ohrms_loan installed)
- [ ] Should show active loans count
- [ ] Widget should only show if employee has loans

#### Test Salary Advance Status
- [ ] Check if salary advance widget appears (if ent_ohrms_salary_advance installed)
- [ ] Should show pending advance requests
- [ ] Widget should only show if employee has advances

#### Test Insurance Status
- [ ] Check if insurance widget appears (if ent_hr_insurance installed)
- [ ] Should show active insurance policies
- [ ] Widget should only show if employee has insurance

#### Test Contract Renewals
- [ ] Check if contract renewals widget appears (if hr.contract exists)
- [ ] Should show upcoming renewals (next 60 days)
- [ ] Widget should only show if contracts are expiring

### 4. Performance Testing

#### Loading States
- [ ] Check if loading overlay appears when data is loading
- [ ] Loading spinner should be visible
- [ ] Loading should disappear when data is loaded

#### Error Handling
- [ ] Disable a module (e.g., hr_attendance)
- [ ] Dashboard should load without errors
- [ ] Missing module widgets should not appear
- [ ] No JavaScript errors in console

### 5. Responsive Design Testing

#### Desktop (>1200px)
- [ ] All widgets display properly
- [ ] Layout is correct
- [ ] No overflow issues

#### Tablet (768px - 1200px)
- [ ] Widgets adjust to smaller width
- [ ] Quick actions wrap properly
- [ ] Metrics widgets stack correctly

#### Mobile (<768px)
- [ ] Dashboard switches to mobile layout
- [ ] Employee section collapses properly
- [ ] All widgets are accessible
- [ ] Touch interactions work

### 6. Dark Mode Testing

#### Visual Checks
- [ ] Background colors change to dark theme
- [ ] Text colors are readable
- [ ] Widgets have proper contrast
- [ ] Charts remain visible
- [ ] Icons are visible

#### Functionality
- [ ] All buttons work in dark mode
- [ ] Links are clickable
- [ ] Forms are usable
- [ ] No visual glitches

### 7. Browser Compatibility

#### Chrome/Edge
- [ ] All features work
- [ ] No console errors
- [ ] Performance is good

#### Firefox
- [ ] All features work
- [ ] CSS animations work
- [ ] No layout issues

#### Safari
- [ ] All features work
- [ ] Dark mode works
- [ ] Responsive design works

### 8. Integration Testing

#### With hr_attendance
- [ ] Attendance button appears
- [ ] Check in/out works
- [ ] State updates correctly

#### With ent_employee_documents_expiry
- [ ] Document button appears
- [ ] Expiry count is accurate
- [ ] Link opens correct view

#### With ent_ohrms_loan
- [ ] Loan widget appears
- [ ] Loan data is accurate
- [ ] No errors if no loans

#### With ent_ohrms_salary_advance
- [ ] Salary advance widget appears
- [ ] Advance data is accurate
- [ ] No errors if no advances

#### With ent_hr_insurance
- [ ] Insurance widget appears
- [ ] Insurance data is accurate
- [ ] No errors if no insurance

### 9. Error Scenarios

#### Missing Modules
- [ ] Dashboard loads without errors
- [ ] Missing widgets don't appear
- [ ] No JavaScript errors

#### No Employee Record
- [ ] Dashboard loads gracefully
- [ ] Employee section shows placeholder
- [ ] No errors in console

#### Network Issues
- [ ] Loading states appear
- [ ] Error messages are user-friendly
- [ ] Dashboard doesn't crash

## Expected Results

### Success Criteria
1. ✅ All quick actions work correctly
2. ✅ Additional metrics display accurately
3. ✅ Loading states appear during data fetch
4. ✅ Error handling prevents crashes
5. ✅ Dark mode works and persists
6. ✅ Responsive design works on all screen sizes
7. ✅ No JavaScript console errors
8. ✅ Performance is acceptable (<2s load time)

### Known Limitations
- moment.js dependency (loaded via CDN)
- Some widgets depend on optional modules
- Dark mode preference stored in localStorage

## Debugging Tips

### If Quick Actions Don't Appear
1. Check browser console for errors
2. Verify modules are installed
3. Check if user has employee record
4. Verify action IDs exist

### If Metrics Don't Load
1. Check backend logs
2. Verify module availability checks
3. Check user permissions
4. Verify data exists

### If Dark Mode Doesn't Work
1. Check localStorage in browser DevTools
2. Verify CSS classes are applied
3. Check for CSS conflicts
4. Clear browser cache

## Post-Testing

### Performance Metrics
- [ ] Page load time: _____ seconds
- [ ] Time to interactive: _____ seconds
- [ ] API call response time: _____ ms

### Issues Found
- [ ] Issue 1: _______________
- [ ] Issue 2: _______________
- [ ] Issue 3: _______________

### Recommendations
- [ ] Recommendation 1: _______________
- [ ] Recommendation 2: _______________

