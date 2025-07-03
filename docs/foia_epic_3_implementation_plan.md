# Epic 3 Implementation Plan: FOIA Response Assistant

## Current Status

### ✅ Phase 1: Foundation & Core Services (Days 1-2) - COMPLETE
- **Embedding Service**: Fully implemented with OpenAI integration
- **Embedding Store**: In-memory storage with duplicate detection
- **Document Model**: Enhanced with duplicate detection fields
- **Audit Infrastructure**: Partially implemented (model only)

### ✅ Phase 2: Duplicate Detection Feature (Days 3-4) - COMPLETE  
- **UI Integration**: Status panel shows embedding progress
- **Finalize Tab**: Duplicate status column and selection tools
- **Processing**: Two-phase workflow with embedding generation
- **Performance**: Parallel processing for large document sets

### ❌ Phase 3: Audit Trail Feature (Days 5-6) - NOT STARTED
- Audit tab not implemented
- Audit manager service not created
- Audit logging integration pending

### ❌ Phase 4: Integration & Testing (Days 7-8) - NOT STARTED

## Overview

This document provides a detailed phased implementation plan for Epic 3 of the FOIA Response Assistant. The plan is structured to deliver working functionality incrementally while minimizing risk and ensuring proper testing at each phase.

## Implementation Timeline

**Total Duration**: 7-8 working days
- Phase 1: Foundation & Core Services (Days 1-2)
- Phase 2: Duplicate Detection Feature (Days 3-4)
- Phase 3: Audit Trail Feature (Days 5-6)
- Phase 4: Integration & Testing (Days 7-8)

## Phase 1: Foundation & Core Services (Days 1-2) ✅ COMPLETE

### Day 1: Core Services Setup

#### Morning (4 hours)
1. **Create Core Service Classes**
   - [x] Create `src/services/embedding_service.py`
     - Implement `EmbeddingService` class
     - Add OpenAI client initialization
     - Implement `generate_embedding()` method
     - Implement `generate_content_hash()` method
     - Add error handling and logging
   
   - [x] Create `src/services/embedding_store.py`
     - Implement `EmbeddingStore` class
     - Add in-memory storage dictionaries
     - Implement `add_embedding()` method
     - Implement `find_exact()` method (renamed from find_exact_duplicate)
     - Implement `find_similar()` with cosine similarity
     - Implement `clear_request()` method
     - Added `to_dict()` and `from_dict()` for serialization

2. **Update Document Model**
   - [x] Modify `src/models/document.py`
     - Add duplicate detection fields:
       - `is_duplicate: bool = False`
       - `duplicate_of: Optional[str] = None`
       - `similarity_score: Optional[float] = None`
       - `content_hash: Optional[str] = None`
       - `embedding_generated: bool = False`

#### Afternoon (4 hours)
3. **Create Audit Infrastructure**
   - [x] Create `src/models/audit.py`
     - Implement `AuditEntry` dataclass
     - Add `to_dict()` method for CSV export
   
   - [ ] Create `src/processing/audit_manager.py` (NOT IMPLEMENTED)
     - Implement `AuditManager` class
     - Add logging methods:
       - `log_classification()`
       - `log_review()`
       - `log_view()`
       - `log_export()`
       - `log_error()`
     - Implement `get_entries()` with filtering
     - Implement `export_csv()`
     - Implement `get_all_documents()`

4. **Update Dependencies**
   - [x] Add numpy to requirements.txt
   - [x] Verify OpenAI SDK version supports embeddings
   - [x] Update development dependencies

### Day 1 Deliverables ✅
- Working embedding service with tests
- In-memory embedding store implementation
- Enhanced document model
- Partial audit infrastructure (audit model only)
- Updated project dependencies

### Day 2: Processing Integration Foundation

#### Morning (4 hours)
1. **Enhance Processing Worker**
   - [x] Update `src/processing/worker.py`
     - Add embedding_store parameter to constructor
     - Add new Qt signals:
       - `embedding_progress = pyqtSignal(int, int)`
       - `duplicates_found = pyqtSignal(int)`
       - `status_updated = pyqtSignal(str)`
       - `embedding_worker_count = pyqtSignal(int)`
       - `embedding_rate_updated = pyqtSignal(float)`
     - Create `_document_metadata` dictionary
     - Implement two-phase processing structure

2. **Implement Embedding Phase**
   - [x] Add `_generate_embeddings_phase()` method
     - Document loading logic
     - Content hash generation
     - Exact duplicate checking
     - Embedding generation with progress updates
     - Near-duplicate detection
     - Duplicate marking logic
     - Store metadata for classification phase
   - [x] Add both sequential and parallel embedding generation methods

#### Afternoon (4 hours)
3. **Update Parallel Processing**
   - [x] Create `src/processing/parallel_embeddings.py`
     - Implement `ParallelEmbeddingProcessor` class
     - Create worker pool for embedding generation
     - Pass embedding results back to main process
     - Real-time duplicate detection during processing
     - Progress tracking and rate calculation
   
   - [x] Modify `src/processing/parallel_worker.py`
     - Pass embedding metadata to workers
     - Update task distribution logic
     - Ensure duplicate documents are still processed
     - Maintain progress aggregation

4. **Integration Testing Setup**
   - [x] System tested with real documents
   - [x] Request isolation verified in embedding store
   - [x] Performance optimizations implemented

### Day 2 Deliverables ✅
- Enhanced processing worker with embedding phase
- Working duplicate detection logic
- Parallel embedding generation support
- Updated parallel document processing
- Tested with production documents

## Phase 2: Duplicate Detection Feature (Days 3-4) ✅ COMPLETE

### Day 3: UI Integration for Duplicates

#### Morning (4 hours)
1. **Status Panel Enhancement**
   - [x] Update `src/gui/widgets/status_panel.py`
     - Add embedding progress bar widget
     - Add "Embeddings Generated" label
     - Add "Duplicates Found" label
     - Implement `update_embedding_progress()` method
     - Implement `update_duplicate_count()` method
     - Update layout to accommodate new widgets

2. **Connect Processing Signals**
   - [x] Update `src/gui/tabs/intake_tab.py`
     - Connect embedding_progress signal to status panel
     - Connect duplicates_found signal to status panel
     - Pass embedding_store to ProcessingWorker
     - Update status messages during processing

#### Afternoon (4 hours)
3. **Finalize Tab Enhancement**
   - [x] Update `src/gui/tabs/finalize_tab.py`
     - Add "Duplicate Status" column to table
     - Modify `_setup_ui()` to include new column
     - Add "Select All Non-Duplicates" button
     - Implement `_select_non_duplicates()` method
     - Update `_populate_table()` with duplicate information
     - Style duplicate entries (gray text)
     - Set checkbox defaults based on duplicate status
     - Group duplicates with their originals

4. **Document Viewer Updates**
   - [x] Update document details display
     - Show duplicate status in metadata (in finalize tab labels)
     - Display similarity score for near-duplicates
     - Show "Duplicate of: [filename]" relationship

### Day 3 Deliverables ✅
- Enhanced status panel with embedding progress
- Updated finalize tab with duplicate columns
- Working "Select All Non-Duplicates" functionality
- Visual indicators for duplicate documents

### Day 4: Testing & Optimization

#### Morning (4 hours)
1. **Comprehensive Testing**
   - [x] Test exact duplicate detection accuracy
   - [x] Test near-duplicate detection (85% threshold)
   - [x] Verify request isolation (no cross-contamination)
   - [x] Test UI updates during processing
   - [x] Verify export excludes unchecked duplicates
   - [x] Test with large document sets (tested in production)

2. **Performance Optimization**
   - [x] Measure embedding generation time
   - [x] Optimize batch processing (parallel embedding processor implemented)
   - [x] Test memory usage with large document sets
   - [x] Implement progress throttling if needed

#### Afternoon (4 hours)
3. **Edge Case Handling**
   - [x] Handle embedding API failures gracefully
   - [x] Test with empty documents
   - [x] Test with very large documents (content truncation)
   - [x] Handle rate limiting from OpenAI
   - [x] Test Unicode and special characters

4. **Documentation**
   - [x] Document duplicate detection workflow
   - [ ] Create user guide for duplicate features (not implemented)
   - [x] Document API usage and costs
   - [x] Update system architecture diagram (updated in docs/foia_system_architecture.md)

### Day 4 Deliverables ✅
- Fully tested duplicate detection system
- Performance benchmarks documented
- Edge cases handled properly
- System architecture documentation updated

## Phase 3: Audit Trail Feature (Days 5-6)

### Day 5: Audit System Integration

#### Morning (4 hours)
1. **Create Audit Tab**
   - [ ] Create `src/gui/tabs/audit_tab.py`
     - Implement `AuditTab` class
     - Create two-panel layout (30/70 split)
     - Implement document list with checkboxes
     - Implement audit trail display area
     - Add dynamic export button
     - Implement `_populate_document_list()` method
     - Implement `_display_audit_entries()` method

2. **Wire Up Audit Tab**
   - [ ] Update `src/gui/main_window.py`
     - Add Audit tab to tab widget
     - Pass audit_manager to audit tab
     - Add tab to refresh cycle
     - Update tab styling

#### Afternoon (4 hours)
3. **Integrate Audit Logging - Classification**
   - [ ] Update `src/langgraph/nodes/classifier.py`
     - Add audit_manager to state
     - Log successful classifications
     - Log classification errors
     - Include confidence scores in logs

4. **Integrate Audit Logging - Reviews**
   - [ ] Update `src/gui/tabs/review_tab.py`
     - Pass audit_manager to constructor
     - Log review decisions
     - Distinguish approvals from overrides
     - Log document views in review tab

### Day 5 Deliverables
- Working audit tab with document filtering
- Classification events logged to audit trail
- Review decisions logged with override detection
- Basic audit display functionality

### Day 6: Complete Audit Integration

#### Morning (4 hours)
1. **Document View Logging**
   - [ ] Update `src/gui/widgets/document_viewer.py`
     - Add audit_manager parameter
     - Log all document views with tab context
     - Pass tab name for context
   
   - [ ] Update all tabs to pass audit_manager
     - Review tab document viewer
     - Finalize tab document viewer
     - Any other document display locations

2. **Export Event Logging**
   - [ ] Update export methods in finalize tab
     - Log CSV exports
     - Log JSON exports
     - Log Excel exports
     - Log PDF exports
     - Include document count and selection

#### Afternoon (4 hours)
3. **Audit Export Implementation**
   - [ ] Implement CSV export in audit tab
     - File dialog for save location
     - Progress indication for large exports
     - Success/error messaging
     - Support filtered exports

4. **Testing Audit Features**
   - [ ] Test audit entry creation
   - [ ] Test document filtering
   - [ ] Test CSV export format
   - [ ] Test with multiple requests
   - [ ] Verify chronological ordering
   - [ ] Test export with selections

### Day 6 Deliverables
- Complete audit logging integration
- Working CSV export functionality
- All user actions logged appropriately
- Tested audit trail system

## Phase 4: Integration & Testing (Days 7-8)

### Day 7: System Integration

#### Morning (4 hours)
1. **End-to-End Testing**
   - [ ] Create test scenario with duplicates and reviews
   - [ ] Process documents through full workflow
   - [ ] Verify duplicate detection during processing
   - [ ] Review documents and check audit trail
   - [ ] Export results and verify duplicates excluded
   - [ ] Export audit trail and verify completeness

2. **Cross-Feature Testing**
   - [ ] Test duplicate detection with reprocessing
   - [ ] Verify audit logs capture reprocessing
   - [ ] Test request switching with embeddings
   - [ ] Verify audit entries across requests
   - [ ] Test memory cleanup on request deletion

#### Afternoon (4 hours)
3. **Performance Testing**
   - [ ] Benchmark with 100 documents
   - [ ] Measure memory usage over time
   - [ ] Test UI responsiveness with large audit trail
   - [ ] Optimize any bottlenecks found
   - [ ] Document performance characteristics

4. **Error Handling**
   - [ ] Test graceful degradation
   - [ ] Verify error messages are user-friendly
   - [ ] Test recovery from API failures
   - [ ] Ensure no data loss on errors

### Day 7 Deliverables
- Fully integrated system tested
- Performance benchmarks completed
- Error handling verified
- Cross-feature interactions validated

### Day 8: Polish & Documentation

#### Morning (4 hours)
1. **UI Polish**
   - [ ] Review all UI elements for consistency
   - [ ] Ensure proper spacing and alignment
   - [ ] Verify keyboard navigation works
   - [ ] Test on different screen sizes
   - [ ] Update any missing tooltips or help text

2. **Code Cleanup**
   - [ ] Remove debug print statements
   - [ ] Add missing docstrings
   - [ ] Run code formatter (black)
   - [ ] Run linter (ruff)
   - [ ] Fix any type checking issues (mypy)

#### Afternoon (4 hours)
3. **Documentation Updates**
   - [ ] Update README with new features
   - [ ] Create Epic 3 release notes
   - [ ] Document new UI workflows
   - [ ] Update architecture diagrams
   - [ ] Create troubleshooting guide

4. **Final Testing**
   - [ ] Run full regression test suite
   - [ ] Test fresh installation
   - [ ] Verify all features work together
   - [ ] Create demo scenarios
   - [ ] Prepare presentation materials

### Day 8 Deliverables
- Polished, production-ready code
- Complete documentation
- Release notes prepared
- Demo scenarios ready

## Risk Mitigation Strategies

### Technical Risks

1. **OpenAI API Issues**
   - Mitigation: Implement retry logic with exponential backoff
   - Fallback: Continue processing without embeddings
   - Monitor: Add logging for API failures

2. **Memory Usage**
   - Mitigation: Implement embedding cleanup on request switch
   - Monitor: Add memory usage logging
   - Fallback: Limit number of embeddings stored

3. **Performance Degradation**
   - Mitigation: Make embedding generation optional
   - Monitor: Add timing metrics
   - Fallback: Process in smaller batches

### Schedule Risks

1. **Integration Complexity**
   - Mitigation: Daily integration testing
   - Buffer: Day 8 includes buffer time
   - Escalation: Prioritize core features if needed

2. **Testing Discoveries**
   - Mitigation: Test continuously, not just at end
   - Buffer: Each phase includes testing time
   - Escalation: Document issues for future sprints

## Success Criteria

### Duplicate Detection
- [ ] Detects 100% of exact duplicates
- [ ] Detects 85%+ of near duplicates
- [ ] No false positives in testing
- [ ] Performance impact <20% on processing time
- [ ] Clear UI indicators for duplicates

### Audit Trail
- [ ] All key events logged
- [ ] CSV export works reliably
- [ ] No performance impact on operations
- [ ] Audit entries are immutable
- [ ] Support for filtered exports

### Overall System
- [ ] All existing features continue working
- [ ] No memory leaks introduced
- [ ] UI remains responsive
- [ ] Error handling is robust
- [ ] Documentation is complete

## Post-Implementation Tasks

1. **Monitoring Setup**
   - Track embedding API usage
   - Monitor performance metrics
   - Set up error alerting

2. **User Training**
   - Create training materials
   - Record demo videos
   - Prepare FAQ document

3. **Feedback Collection**
   - Set up feedback mechanism
   - Plan iteration based on user input
   - Document enhancement requests

## Conclusion

This phased implementation plan provides a structured approach to implementing Epic 3 features. The plan emphasizes incremental delivery, continuous testing, and risk mitigation. Each phase builds on the previous one, ensuring a stable and well-tested final product.