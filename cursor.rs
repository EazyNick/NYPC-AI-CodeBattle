use std::{
    fmt::{self, Display, Formatter},
    io::{self, BufRead, Write, stdout},
    str::FromStr,
    collections::HashMap,
};

/// 가능한 주사위 규칙들을 나타내는 enum
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum DiceRule {
    One,        // 1이 나온 주사위에 적힌 수의 합 × 1000점
    Two,        // 2가 나온 주사위에 적힌 수의 합 × 1000점
    Three,      // 3이 나온 주사위에 적힌 수의 합 × 1000점
    Four,       // 4가 나온 주사위에 적힌 수의 합 × 1000점
    Five,       // 5가 나온 주사위에 적힌 수의 합 × 1000점
    Six,        // 6이 나온 주사위에 적힌 수의 합 × 1000점
    Choice,     // 다섯 개의 주사위에 적힌 모든 수의 합 × 1000점
    FourOfAKind, // 같은 수가 적힌 주사위가 4개 있다면 모든 수의 합 × 1000점
    FullHouse,  // 3개가 같고 2개가 같으면 모든 수의 합 × 1000점
    SmallStraight, // 4개가 연속되면 15000점
    LargeStraight, // 5개가 연속되면 30000점
    Yacht,      // 5개가 모두 같으면 50000점
}

/// 입찰 방법을 나타내는 구조체
#[derive(Debug, Clone)]
struct Bid {
    /// 입찰 그룹 ('A' 또는 'B')
    group: char,
    /// 입찰 금액 (0 이상 100000 이하)
    amount: i32,
}

/// 주사위 배치 방법을 나타내는 구조체
#[derive(Debug, Clone)]
struct DicePut {
    /// 배치할 점수 규칙
    rule: DiceRule,
    /// 배치할 주사위 5개 목록
    dice: [i32; 5],
}

/// 플레이어의 현재 상태를 관리하는 구조체
struct GameState {
    /// 현재 보유한 주사위 목록
    dice: Vec<i32>,
    /// 각 규칙별 획득 점수 (사용하지 않았다면 None)
    rule_score: [Option<i32>; 12],
    /// 입찰로 얻거나 잃은 총 점수
    bid_score: i32,
}

/// 게임 전체 상태를 관리하는 구조체
struct Game {
    /// 내 팀의 현재 상태
    my_state: GameState,
    /// 상대 팀의 현재 상태
    opp_state: GameState,
    /// 현재 턴 번호 (1부터 시작)
    current_round: i32,
    /// 상대방의 각 턴별 입찰 가격 저장 (턴 번호 -> 입찰 가격)
    opponent_bids: HashMap<i32, i32>,
    /// 상대방이 YACHT를 완성했는지 여부
    opponent_yacht_completed: bool,
}

impl Game {
    /// 새로운 게임 인스턴스 생성
    fn new() -> Self {
        Game {
            my_state: GameState::new(),
            opp_state: GameState::new(),
            current_round: 0,  // 0으로 시작하여 첫 번째 ROLL에서 1로 증가
            opponent_bids: HashMap::new(),
            opponent_yacht_completed: false,
        }
    }
    
    /// 주사위 그룹에서 가장 많이 중복된 숫자의 개수를 반환하는 함수
    fn get_max_duplicate_count(&self, dice_group: &[i32]) -> i32 {
        let mut counts = [0; 7];  // 1~6까지의 개수 (인덱스 0은 사용하지 않음)
        
        // 각 숫자의 개수 세기
        for &dice in dice_group {
            counts[dice as usize] += 1;
        }
        
        // 가장 많이 중복된 숫자의 개수 반환
        *counts.iter().skip(1).max().unwrap()
    }
    
    /// 상대방의 입찰 가격을 저장하는 함수
    fn save_opponent_bid(&mut self, round: i32, bid_amount: i32) {
        self.opponent_bids.insert(round, bid_amount);
    }
    
    /// 간단한 랜덤 함수 (시드 없이 현재 시간 기반)
    fn random_between(&self, min: i32, max: i32) -> i32 {
        use std::time::{SystemTime, UNIX_EPOCH};
        let time = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos() as u64;
        min + (time % (max - min + 1) as u64) as i32
    }
    
    /// 상대방이 YACHT를 완성했는지 확인하는 함수
    fn check_opponent_yacht_completion(&mut self) {
        // 상대방이 YACHT 규칙을 사용했는지 확인
        if let Some(score) = self.opp_state.rule_score[DiceRule::Yacht as usize] {
            if score > 0 {
                self.opponent_yacht_completed = true;
            }
        }
    }
    
    /// YACHT 방해가 필요한지 확인하는 함수
    fn should_block_yacht(&self, dice_a: &[i32], dice_b: &[i32]) -> Option<(char, i32)> {
        // 상대방이 이미 YACHT를 완성했다면 방해하지 않음
        if self.opponent_yacht_completed {
            return None;
        }
        
        // 상대방이 4개 중복을 가지고 있는지 확인
        let opp_dice = &self.opp_state.dice;
        if opp_dice.len() < 4 {
            return None;
        }
        
        let mut opp_counts = [0; 7];  // 상대방 주사위 개수
        for &dice in opp_dice {
            opp_counts[dice as usize] += 1;
        }
        
        // 상대방이 4개 중복을 가지고 있는지 확인
        let mut four_duplicate_number = None;
        for i in 1..=6 {
            if opp_counts[i] >= 4 {
                four_duplicate_number = Some(i);
                break;
            }
        }
        
        if let Some(target_number) = four_duplicate_number {
            // A그룹과 B그룹에서 해당 숫자가 몇 개 있는지 확인
            let count_a = dice_a.iter().filter(|&&d| d == target_number as i32).count();
            let count_b = dice_b.iter().filter(|&&d| d == target_number as i32).count();
            
            // 해당 숫자를 얻을 수 있는 그룹이 하나만 있는지 확인
            if (count_a > 0 && count_b == 0) || (count_a == 0 && count_b > 0) {
                let target_group = if count_a > 0 { 'A' } else { 'B' };
                return Some((target_group, 5001));
            }
        }
        
        None
    }
    
    /// 내가 보유한 주사위에서 가장 많이 중복된 숫자를 찾는 함수
    fn get_my_max_duplicate_number(&self) -> Option<(i32, i32)> {
        let my_dice = &self.my_state.dice;
        if my_dice.is_empty() {
            return None;
        }
        
        let mut counts = [0; 7];  // 1~6까지의 개수 (인덱스 0은 사용하지 않음)
        for &dice in my_dice {
            counts[dice as usize] += 1;
        }
        
        // 가장 많이 중복된 숫자와 그 개수 찾기
        let mut max_count = 0;
        let mut max_number = 0;
        for i in 1..=6 {
            if counts[i] > max_count {
                max_count = counts[i];
                max_number = i;
            }
        }
        
        if max_count > 0 {
            Some((max_number as i32, max_count as i32))
        } else {
            None
        }
    }
    
    /// 내가 보유한 주사위의 중복 패턴을 기반으로 그룹을 선택하는 함수
    fn select_group_based_on_my_dice(&self, dice_a: &[i32], dice_b: &[i32]) -> char {
        // 내가 보유한 주사위에서 가장 많이 중복된 숫자 찾기
        if let Some((my_max_number, _my_max_count)) = self.get_my_max_duplicate_number() {
            // A그룹과 B그룹에서 해당 숫자가 몇 개 있는지 확인
            let count_a = dice_a.iter().filter(|&&d| d == my_max_number).count();
            let count_b = dice_b.iter().filter(|&&d| d == my_max_number).count();
            
            // 해당 숫자가 더 많이 있는 그룹 선택
            if count_a > count_b {
                return 'A';
            } else if count_b > count_a {
                return 'B';
            } else if count_a == count_b && count_a > 0 {
                // 개수가 같다면 턴에 따라 다르게 처리
                if self.current_round <= 8 {
                    // 1~8턴: 큰 수를 가져오기
                    let sum_a: i32 = dice_a.iter().sum();
                    let sum_b: i32 = dice_b.iter().sum();
                    return if sum_a > sum_b { 'A' } else { 'B' };
                } else {
                    // 9턴 이후: 남은 조합에 따라 다르게 처리
                    return self.select_group_by_remaining_combinations(dice_a, dice_b);
                }
            }
        }
        
        // 기본값: 합이 높은 쪽 선택
        let sum_a: i32 = dice_a.iter().sum();
        let sum_b: i32 = dice_b.iter().sum();
        if sum_a > sum_b { 'A' } else { 'B' }
    }
    
    /// 남은 조합에 따라 그룹을 선택하는 함수 (9턴 이후)
    fn select_group_by_remaining_combinations(&self, dice_a: &[i32], dice_b: &[i32]) -> char {
        // 사용하지 않은 규칙들 확인
        let unused_rules: Vec<usize> = self.my_state.rule_score
            .iter()
            .enumerate()
            .filter_map(|(i, &score)| if score.is_none() { Some(i) } else { None })
            .collect();
        
        // 각 그룹에서 사용할 수 있는 조합 점수 계산
        let score_a = self.calculate_potential_score(dice_a, &unused_rules);
        let score_b = self.calculate_potential_score(dice_b, &unused_rules);
        
        if score_a > score_b { 'A' } else { 'B' }
    }
    
    /// 주사위 그룹에서 사용할 수 있는 잠재적 점수 계산
    fn calculate_potential_score(&self, dice: &[i32], unused_rules: &[usize]) -> i32 {
        let mut max_score = 0;
        
        for &rule_index in unused_rules {
            if let Some(rule) = DiceRule::from_usize(rule_index) {
                // 각 규칙에 대해 가능한 최고 점수 계산
                let score = self.calculate_rule_potential_score(dice, rule);
                max_score = max_score.max(score);
            }
        }
        
        max_score
    }
    
    /// 특정 규칙에 대한 잠재적 점수 계산
    fn calculate_rule_potential_score(&self, dice: &[i32], rule: DiceRule) -> i32 {
        match rule {
            DiceRule::One => dice.iter().filter(|&&d| d == 1).sum::<i32>() * 1000,
            DiceRule::Two => dice.iter().filter(|&&d| d == 2).sum::<i32>() * 1000,
            DiceRule::Three => dice.iter().filter(|&&d| d == 3).sum::<i32>() * 1000,
            DiceRule::Four => dice.iter().filter(|&&d| d == 4).sum::<i32>() * 1000,
            DiceRule::Five => dice.iter().filter(|&&d| d == 5).sum::<i32>() * 1000,
            DiceRule::Six => dice.iter().filter(|&&d| d == 6).sum::<i32>() * 1000,
            DiceRule::Choice => dice.iter().sum::<i32>() * 1000,
            DiceRule::FourOfAKind => {
                let mut counts = [0; 7];
                for &d in dice {
                    counts[d as usize] += 1;
                }
                if counts.iter().skip(1).any(|&c| c >= 4) {
                    dice.iter().sum::<i32>() * 1000
                } else {
                    0
                }
            }
            DiceRule::FullHouse => {
                let mut counts = [0; 7];
                for &d in dice {
                    counts[d as usize] += 1;
                }
                let has_pair = counts.iter().skip(1).any(|&c| c == 2 || c == 5);
                let has_triple = counts.iter().skip(1).any(|&c| c == 3 || c == 5);
                if has_pair && has_triple {
                    dice.iter().sum::<i32>() * 1000
                } else {
                    0
                }
            }
            DiceRule::SmallStraight => {
                let mut has = [false; 7];
                for &d in dice {
                    has[d as usize] = true;
                }
                if (has[1] && has[2] && has[3] && has[4]) ||
                   (has[2] && has[3] && has[4] && has[5]) ||
                   (has[3] && has[4] && has[5] && has[6]) {
                    15000
                } else {
                    0
                }
            }
            DiceRule::LargeStraight => {
                let mut has = [false; 7];
                for &d in dice {
                    has[d as usize] = true;
                }
                if (has[1] && has[2] && has[3] && has[4] && has[5]) ||
                   (has[2] && has[3] && has[4] && has[5] && has[6]) {
                    30000
                } else {
                    0
                }
            }
            DiceRule::Yacht => {
                let mut counts = [0; 7];
                for &d in dice {
                    counts[d as usize] += 1;
                }
                if counts.iter().skip(1).any(|&c| c == 5) {
                    50000
                } else {
                    0
                }
            }
        }
    }
    // ================================ [필수 구현] ================================
    // ============================================================================
    /// 주사위가 주어졌을 때, 어디에 얼마만큼 베팅할지 정하는 함수
    /// 입찰할 그룹과 베팅 금액을 pair로 묶어서 반환
    // ============================================================================
    fn calculate_bid(&self, dice_a: &[i32], dice_b: &[i32]) -> Bid {
        // YACHT 방해가 필요한지 먼저 확인
        if let Some((group, amount)) = self.should_block_yacht(dice_a, dice_b) {
            return Bid { group, amount };
        }
        
        // 내가 보유한 주사위의 중복 패턴을 기반으로 그룹 선택
        let group = self.select_group_based_on_my_dice(dice_a, dice_b);
        
        // 첫 번째 턴인 경우 중복된 숫자가 가장 많은 그룹 선택
        if self.current_round == 1 {
            // 각 그룹에서 가장 많이 중복된 숫자의 개수 계산
            let max_count_a = self.get_max_duplicate_count(dice_a);
            let max_count_b = self.get_max_duplicate_count(dice_b);
            
            // 중복이 더 많은 그룹 선택
            let (_, max_count) = if max_count_a >= max_count_b {
                ('A', max_count_a)
            } else {
                ('B', max_count_b)
            };
            
            let amount = match max_count {
                3 => 1001,  // 3개 중복시 1001 입찰
                4 => 2001,  // 4개 중복시 2001 입찰
                _ => 1,     // 그 외에는 1 입찰
            };
            
            Bid { group, amount }
        } else if self.current_round == 2 {
            // 두 번째 턴: 상대방의 1번째 턴 입찰가격에 따라 결정
            let first_round_bid = self.opponent_bids.get(&1).unwrap_or(&0);
            let amount = if *first_round_bid > 1 { 101 } else { 0 };
            
            Bid { group, amount }
        } else if self.current_round == 3 {
            // 세 번째 턴: 상대방의 2번째 턴 입찰가격이 홀수/짝수에 따라 랜덤 배팅
            let second_round_bid = self.opponent_bids.get(&2).unwrap_or(&0);
            let amount = if *second_round_bid % 2 == 1 {
                // 홀수면 2, 3 중 랜덤
                self.random_between(2, 3)
            } else {
                // 짝수면 0, 1 중 랜덤
                self.random_between(0, 1)
            };
            
            Bid { group, amount }
        } else {
            // 4번째 턴 이후: 상대방의 2번째 턴 입찰가격이 홀수/짝수에 따라 랜덤 배팅
            let second_round_bid = self.opponent_bids.get(&2).unwrap_or(&0);
            let amount = if *second_round_bid % 2 == 1 {
                // 홀수면 2, 3 중 랜덤
                self.random_between(2, 3)
            } else {
                // 짝수면 0, 1 중 랜덤
                self.random_between(0, 1)
            };
            
            Bid { group, amount }
        }
    }
    // ============================================================================
    /// 주어진 주사위에 대해 사용할 규칙과 주사위를 정하는 함수
    /// 사용할 규칙과 사용할 주사위의 목록을 pair로 묶어서 반환
    // ============================================================================
    fn calculate_put(&self) -> DicePut {
        // 사용하지 않은 규칙들 찾기
        let unused_rules: Vec<usize> = self.my_state.rule_score
            .iter()
            .enumerate()
            .filter_map(|(i, &score)| if score.is_none() { Some(i) } else { None })
            .collect();
        
        // 각 규칙에 대해 최적의 주사위 조합과 점수 계산
        let mut best_rule = 0;
        let mut best_dice = [0; 5];
        let mut best_score = 0;
        
        for &rule_index in &unused_rules {
            if let Some(rule) = DiceRule::from_usize(rule_index) {
                let (dice, score) = self.find_best_dice_for_rule(rule);
                if score > best_score {
                    best_score = score;
                    best_rule = rule_index;
                    best_dice = dice;
                }
            }
        }
        
        DicePut {
            rule: DiceRule::from_usize(best_rule).unwrap(),
            dice: best_dice,
        }
    }
    
    /// 특정 규칙에 대해 최적의 주사위 조합을 찾는 함수
    fn find_best_dice_for_rule(&self, rule: DiceRule) -> ([i32; 5], i32) {
        let my_dice = &self.my_state.dice;
        let mut best_dice = [0; 5];
        let mut best_score = 0;
        
        // 모든 가능한 5개 주사위 조합을 시도
        if my_dice.len() >= 5 {
            // 간단한 방법: 가장 높은 점수를 주는 조합 찾기
            let combinations = self.generate_dice_combinations(my_dice);
            
            for dice in combinations {
                let score = self.calculate_rule_potential_score(&dice, rule);
                if score > best_score {
                    best_score = score;
                    best_dice = dice;
                }
            }
        }
        
        (best_dice, best_score)
    }
    
    /// 주사위 목록에서 가능한 5개 조합들을 생성하는 함수
    fn generate_dice_combinations(&self, dice: &[i32]) -> Vec<[i32; 5]> {
        let mut combinations = Vec::new();
        
        if dice.len() < 5 {
            return combinations;
        }
        
        // 간단한 방법: 처음 5개, 마지막 5개, 그리고 중복이 많은 조합들
        if dice.len() >= 5 {
            // 처음 5개
            let first_five: [i32; 5] = dice[..5].try_into().unwrap();
            combinations.push(first_five);
            
            // 마지막 5개
            if dice.len() > 5 {
                let last_five: [i32; 5] = dice[dice.len()-5..].try_into().unwrap();
                combinations.push(last_five);
            }
            
            // 중복이 많은 조합들 찾기
            let mut counts = [0; 7];
            for &d in dice {
                counts[d as usize] += 1;
            }
            
            // 가장 많이 중복된 숫자들로 조합 만들기
            for target_num in 1..=6 {
                if counts[target_num as usize] >= 3 {
                    let mut combination = [target_num; 5];
                    let mut used = 0;
                    
                    // 해당 숫자들을 먼저 채우기
                    for (i, &d) in dice.iter().enumerate() {
                        if d == target_num && used < 5 {
                            combination[used] = d;
                            used += 1;
                        }
                    }
                    
                    // 나머지는 다른 숫자들로 채우기
                    for (i, &d) in dice.iter().enumerate() {
                        if d != target_num && used < 5 {
                            combination[used] = d;
                            used += 1;
                        }
                    }
                    
                    combinations.push(combination);
                }
            }
            
            // 연속된 숫자 조합들 (STRAIGHT용)
            for start in 1..=2 {
                let mut combination = [0; 5];
                let mut used = 0;
                
                for num in start..start+5 {
                    if num <= 6 {
                        combination[used] = num;
                        used += 1;
                    }
                }
                
                if used == 5 {
                    combinations.push(combination);
                }
            }
        }
        
        combinations
    }
    // ============================== [필수 구현 끝] ==============================

    /// 입찰 결과를 받아서 상태 업데이트
    fn update_get(
        &mut self,
        dice_a: &[i32],      // A그룹 주사위 5개
        dice_b: &[i32],      // B그룹 주사위 5개
        my_bid: &Bid,        // 내 입찰 정보
        opp_bid: &Bid,       // 상대 입찰 정보
        my_group: char,      // 내가 가져간 그룹
    ) {
        // 상대방의 입찰 가격 저장
        self.save_opponent_bid(self.current_round, opp_bid.amount);
        
        // 그룹에 따라 주사위 분배
        if my_group == 'A' {
            self.my_state.add_dice(dice_a);   // 내가 A그룹 가져감
            self.opp_state.add_dice(dice_b);  // 상대가 B그룹 가져감
        } else {
            self.my_state.add_dice(dice_b);   // 내가 B그룹 가져감
            self.opp_state.add_dice(dice_a);  // 상대가 A그룹 가져감
        }
        // 입찰 결과에 따른 점수 반영
        let my_bid_ok = my_bid.group == my_group;  // 내 입찰 성공 여부
        self.my_state.bid(my_bid_ok, my_bid.amount);
        let opp_group = if my_group == 'A' { 'B' } else { 'A' };  // 상대가 가져간 그룹
        let opp_bid_ok = opp_bid.group == opp_group;  // 상대 입찰 성공 여부
        self.opp_state.bid(opp_bid_ok, opp_bid.amount);
    }
    /// 내가 주사위를 배치한 결과 반영
    fn update_put(&mut self, put: &DicePut) {
        self.my_state.use_dice(put);
    }
    /// 상대가 주사위를 배치한 결과 반영
    fn update_set(&mut self, put: &DicePut) {
        self.opp_state.use_dice(put);
        // 상대방이 YACHT를 완성했는지 확인
        self.check_opponent_yacht_completion();
    }
}

impl GameState {
    /// 새로운 게임 상태 생성
    fn new() -> Self {
        GameState {
            dice: Vec::new(),           // 빈 주사위 목록으로 시작
            rule_score: [None; 12],     // 모든 규칙 미사용 상태
            bid_score: 0,               // 입찰 점수 0으로 시작
        }
    }

    /// 현재까지 획득한 총 점수 계산 (기본 점수 + 보너스 + 조합 점수 + 입찰 점수)
    fn get_total_score(&self) -> i32 {
        let mut basic = 0;      // 기본 점수 (ONE~SIX)
        let mut combination = 0; // 조합 점수 (CHOICE~YACHT)
        let mut bonus = 0;      // 보너스 점수
        // 기본 점수 규칙 계산 (ONE ~ SIX)
        for i in 0..6 {
            if let Some(score) = self.rule_score[i] {
                basic += score;
            }
        }
        // 보너스 점수 계산 (기본 규칙 63000점 이상시 35000점 보너스)
        if basic >= 63000 {
            bonus += 35000;
        }
        // 조합 점수 규칙 계산 (CHOICE ~ YACHT)
        for i in 6..12 {
            if let Some(score) = self.rule_score[i] {
                combination += score;
            }
        }
        basic + bonus + combination + self.bid_score
    }

    /// 입찰 결과에 따른 점수 반영
    fn bid(&mut self, is_successful: bool, amount: i32) {
        if is_successful {
            self.bid_score -= amount; // 성공시 베팅 금액만큼 점수 차감
        } else {
            self.bid_score += amount; // 실패시 베팅 금액만큼 점수 획득
        }
    }

    /// 주사위 획득 (새로운 주사위들을 기존 목록에 추가)
    fn add_dice(&mut self, new_dice: &[i32]) {
        self.dice.extend_from_slice(new_dice);
    }

    /// 주사위 사용 (점수 규칙에 따라 주사위 사용)
    fn use_dice(&mut self, put: &DicePut) {
        // 이미 사용한 규칙인지 확인
        assert!(
            self.rule_score[put.rule as usize].is_none(),
            "Rule already used"
        );
        // 사용할 주사위들을 목록에서 제거
        for &d in &put.dice {
            // 주사위 목록에 없는 주사위가 있는지 확인하고 주사위 제거
            let pos = self
                .dice
                .iter()
                .position(|&x| x == d)
                .expect("Invalid dice");
            self.dice.remove(pos);
        }
        // 해당 규칙의 점수 계산 및 저장
        self.rule_score[put.rule as usize] = Some(Self::calculate_score(put));
    }

    /// 규칙에 따른 점수를 계산하는 함수
    #[allow(clippy::nonminimal_bool)]
    fn calculate_score(put: &DicePut) -> i32 {
        let dice = &put.dice;  // 사용할 주사위 5개
        match put.rule {
            // 기본 규칙 점수 계산 (해당 숫자에 적힌 수의 합 × 1000점)
            DiceRule::One => dice.iter().filter(|&&d| d == 1).sum::<i32>() * 1000,
            DiceRule::Two => dice.iter().filter(|&&d| d == 2).sum::<i32>() * 1000,
            DiceRule::Three => dice.iter().filter(|&&d| d == 3).sum::<i32>() * 1000,
            DiceRule::Four => dice.iter().filter(|&&d| d == 4).sum::<i32>() * 1000,
            DiceRule::Five => dice.iter().filter(|&&d| d == 5).sum::<i32>() * 1000,
            DiceRule::Six => dice.iter().filter(|&&d| d == 6).sum::<i32>() * 1000,
            DiceRule::Choice => dice.iter().sum::<i32>() * 1000, // 주사위에 적힌 모든 수의 합 × 1000점
            DiceRule::FourOfAKind => {
                // 같은 수가 적힌 주사위가 4개 있다면, 주사위에 적힌 모든 수의 합 × 1000점, 아니면 0
                let ok = (1..=6).any(|i| dice.iter().filter(|&&d| d == i).count() >= 4);
                if ok {
                    dice.iter().sum::<i32>() * 1000
                } else {
                    0
                }
            }
            DiceRule::FullHouse => {
                // 3개의 주사위에 적힌 수가 서로 같고, 다른 2개의 주사위에 적힌 수도 서로 같으면 주사위에 적힌 모든 수의 합 × 1000점, 아닐 경우 0점
                let mut pair = false;   // 2개가 같은 숫자가 있는지
                let mut triple = false; // 3개가 같은 숫자가 있는지
                for i in 1..=6 {
                    let cnt = dice.iter().filter(|&&d| d == i).count();
                    // 5개 모두 같은 숫자일 때도 인정
                    if cnt == 2 || cnt == 5 {
                        pair = true;
                    }
                    if cnt == 3 || cnt == 5 {
                        triple = true;
                    }
                }
                if pair && triple {
                    dice.iter().sum::<i32>() * 1000
                } else {
                    0
                }
            }
            DiceRule::SmallStraight => {
                // 4개의 주사위에 적힌 수가 1234, 2345, 3456중 하나로 연속되어 있을 때, 15000점, 아닐 경우 0점
                let e1 = dice.iter().filter(|&&d| d == 1).count() > 0;  // 1이 있는지
                let e2 = dice.iter().filter(|&&d| d == 2).count() > 0;  // 2가 있는지
                let e3 = dice.iter().filter(|&&d| d == 3).count() > 0;  // 3이 있는지
                let e4 = dice.iter().filter(|&&d| d == 4).count() > 0;  // 4가 있는지
                let e5 = dice.iter().filter(|&&d| d == 5).count() > 0;  // 5가 있는지
                let e6 = dice.iter().filter(|&&d| d == 6).count() > 0;  // 6이 있는지
                let ok = (e1 && e2 && e3 && e4) || (e2 && e3 && e4 && e5) || (e3 && e4 && e5 && e6);
                if ok { 15000 } else { 0 }
            }
            DiceRule::LargeStraight => {
                // 5개의 주사위에 적힌 수가 12345, 23456중 하나로 연속되어 있을 때, 30000점, 아닐 경우 0점
                let e1 = dice.iter().filter(|&&d| d == 1).count() > 0;  // 1이 있는지
                let e2 = dice.iter().filter(|&&d| d == 2).count() > 0;  // 2가 있는지
                let e3 = dice.iter().filter(|&&d| d == 3).count() > 0;  // 3이 있는지
                let e4 = dice.iter().filter(|&&d| d == 4).count() > 0;  // 4가 있는지
                let e5 = dice.iter().filter(|&&d| d == 5).count() > 0;  // 5가 있는지
                let e6 = dice.iter().filter(|&&d| d == 6).count() > 0;  // 6이 있는지
                let ok = (e1 && e2 && e3 && e4 && e5) || (e2 && e3 && e4 && e5 && e6);
                if ok { 30000 } else { 0 }
            }
            DiceRule::Yacht => {
                // 5개의 주사위에 적힌 수가 모두 같을 때 50000점, 아닐 경우 0점
                let ok = (1..=6).any(|i| dice.iter().filter(|&&d| d == i).count() == 5);
                if ok { 50000 } else { 0 }
            }
        }
    }
}

impl DiceRule {
    /// usize 값을 DiceRule으로 변환
    fn from_usize(value: usize) -> Option<Self> {
        match value {
            0 => Some(DiceRule::One),
            1 => Some(DiceRule::Two),
            2 => Some(DiceRule::Three),
            3 => Some(DiceRule::Four),
            4 => Some(DiceRule::Five),
            5 => Some(DiceRule::Six),
            6 => Some(DiceRule::Choice),
            7 => Some(DiceRule::FourOfAKind),
            8 => Some(DiceRule::FullHouse),
            9 => Some(DiceRule::SmallStraight),
            10 => Some(DiceRule::LargeStraight),
            11 => Some(DiceRule::Yacht),
            _ => None,
        }
    }
}

impl From<DiceRule> for usize {
    /// DiceRule을 usize로 변환
    fn from(rule: DiceRule) -> Self {
        return rule as usize;
    }
}

impl FromStr for DiceRule {
    type Err = String;

    /// 문자열을 DiceRule로 파싱
    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "ONE" => Ok(DiceRule::One),
            "TWO" => Ok(DiceRule::Two),
            "THREE" => Ok(DiceRule::Three),
            "FOUR" => Ok(DiceRule::Four),
            "FIVE" => Ok(DiceRule::Five),
            "SIX" => Ok(DiceRule::Six),
            "CHOICE" => Ok(DiceRule::Choice),
            "FOUR_OF_A_KIND" => Ok(DiceRule::FourOfAKind),
            "FULL_HOUSE" => Ok(DiceRule::FullHouse),
            "SMALL_STRAIGHT" => Ok(DiceRule::SmallStraight),
            "LARGE_STRAIGHT" => Ok(DiceRule::LargeStraight),
            "YACHT" => Ok(DiceRule::Yacht),
            _ => Err(format!("Invalid dice rule: {s}")),
        }
    }
}

impl Display for DiceRule {
    /// DiceRule을 문자열로 출력
    fn fmt(&self, f: &mut Formatter<'_>) -> fmt::Result {
        let s = match self {
            DiceRule::One => "ONE",
            DiceRule::Two => "TWO",
            DiceRule::Three => "THREE",
            DiceRule::Four => "FOUR",
            DiceRule::Five => "FIVE",
            DiceRule::Six => "SIX",
            DiceRule::Choice => "CHOICE",
            DiceRule::FourOfAKind => "FOUR_OF_A_KIND",
            DiceRule::FullHouse => "FULL_HOUSE",
            DiceRule::SmallStraight => "SMALL_STRAIGHT",
            DiceRule::LargeStraight => "LARGE_STRAIGHT",
            DiceRule::Yacht => "YACHT",
        };
        write!(f, "{s}")
    }
}

/// 표준 입력을 통해 명령어를 처리하는 메인 함수
fn main() {
    let stdin = io::stdin();
    let mut game = Game::new();  // 새로운 게임 인스턴스 생성

    // 입찰 라운드에서 나온 주사위들을 저장할 변수들
    let mut dice_a: Option<[i32; 5]> = None;  // A그룹 주사위 5개
    let mut dice_b: Option<[i32; 5]> = None;  // B그룹 주사위 5개
    // 내가 마지막으로 한 입찰 정보를 저장할 변수
    let mut my_bid: Option<Bid> = None;

    // 표준 입력에서 한 줄씩 읽어서 명령어 처리
    for line in stdin.lock().lines() {
        let line = line.unwrap();
        if line.trim().is_empty() {
            continue;  // 빈 줄은 무시
        }

        let parts: Vec<_> = line.split_whitespace().collect();  // 공백으로 명령어 분리
        let command = parts[0];  // 첫 번째 부분이 명령어
        match command {
            "READY" => {
                // 게임 시작 준비 완료
                println!("OK");
                stdout().flush().unwrap();
            }
            "ROLL" => {
                // 주사위 굴리기 결과 받기
                game.current_round += 1;  // 턴 증가
                let str_a = parts[1];  // A그룹 주사위 문자열
                let str_b = parts[2];  // B그룹 주사위 문자열
                let mut dice_a_array = [0; 5];  // A그룹 주사위 배열
                let mut dice_b_array = [0; 5];  // B그룹 주사위 배열
                // 문자열을 숫자 배열로 변환
                for (dice_val, c) in dice_a_array.iter_mut().zip(str_a.chars()) {
                    *dice_val = c.to_digit(10).unwrap() as i32;
                }
                for (dice_val, c) in dice_b_array.iter_mut().zip(str_b.chars()) {
                    *dice_val = c.to_digit(10).unwrap() as i32;
                }
                dice_a = Some(dice_a_array);
                dice_b = Some(dice_b_array);
                // 입찰 계산 및 출력
                my_bid = Some(game.calculate_bid(&dice_a_array, &dice_b_array));
                let Bid { group, amount } = my_bid.as_ref().unwrap();
                println!("BID {group} {amount}");
                stdout().flush().unwrap();
            }
            "GET" => {
                // 주사위 받기 (입찰 결과)
                let get_group = parts[1].chars().next().unwrap();  // 내가 가져간 그룹
                let opp_group = parts[2].chars().next().unwrap();  // 상대가 가져간 그룹
                let opp_score = parts[3].parse::<i32>().unwrap();  // 상대 입찰 점수
                let my_bid_ref = my_bid.as_ref().unwrap();
                // 게임 상태 업데이트
                game.update_get(
                    dice_a.as_ref().unwrap(),
                    dice_b.as_ref().unwrap(),
                    my_bid_ref,
                    &Bid {
                        group: opp_group,
                        amount: opp_score,
                    },
                    get_group,
                );
            }
            "SCORE" => {
                // 주사위 골라서 배치하기 (점수 획득 단계)
                let put = game.calculate_put();
                game.update_put(&put);
                // PUT 명령어 출력
                print!("PUT {} ", put.rule);
                for d in &put.dice {
                    print!("{d}");
                }
                println!();
                stdout().flush().unwrap();
            }
            "SET" => {
                // 상대의 주사위 배치 결과 받기
                let rule: DiceRule = parts[1].parse().unwrap();  // 상대가 사용한 규칙
                let dice_vec: Vec<i32> = parts[2]  // 상대가 사용한 주사위
                    .chars()
                    .map(|c| c.to_digit(10).unwrap() as i32)
                    .collect();
                let dice: [i32; 5] = dice_vec.try_into().unwrap();
                game.update_set(&DicePut { rule, dice });
            }
            "FINISH" => {
                // 게임 종료
                break;
            }
            _ => {
                // 알 수 없는 명령어 처리
                panic!("Invalid command: {command}");
            }
        }
    }
}
