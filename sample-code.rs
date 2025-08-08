use std::{
    fmt::{self, Display, Formatter},
    io::{self, BufRead, Write, stdout},
    str::FromStr,
};

/// 가능한 주사위 규칙들을 나타내는 enum
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum DiceRule {
    One,
    Two,
    Three,
    Four,
    Five,
    Six,
    Choice,
    FourOfAKind,
    FullHouse,
    SmallStraight,
    LargeStraight,
    Yacht,
}

/// 입찰 방법을 나타내는 구조체
#[derive(Debug, Clone)]
struct Bid {
    /// 입찰 그룹 ('A' 또는 'B')
    group: char,
    /// 입찰 금액
    amount: i32,
}

/// 주사위 배치 방법을 나타내는 구조체
#[derive(Debug, Clone)]
struct DicePut {
    /// 배치 규칙
    rule: DiceRule,
    /// 배치할 주사위 목록
    dice: [i32; 5],
}

/// 팀의 현재 상태를 관리하는 구조체
struct GameState {
    /// 현재 보유한 주사위 목록
    dice: Vec<i32>,
    /// 각 규칙별 획득 점수 (사용하지 않았다면 None)
    rule_score: [Option<i32>; 12],
    /// 입찰로 얻거나 잃은 총 점수
    bid_score: i32,
}

/// 게임 상태를 관리하는 구조체
struct Game {
    /// 내 팀의 현재 상태
    my_state: GameState,
    /// 상대 팀의 현재 상태
    opp_state: GameState,
}

impl Game {
    fn new() -> Self {
        Game {
            my_state: GameState::new(),
            opp_state: GameState::new(),
        }
    }
    // ================================ [필수 구현] ================================
    // ============================================================================
    /// 주사위가 주어졌을 때, 어디에 얼마만큼 베팅할지 정하는 함수
    /// 입찰할 그룹과 베팅 금액을 pair로 묶어서 반환
    // ============================================================================
    fn calculate_bid(&self, dice_a: &[i32], dice_b: &[i32]) -> Bid {
        // 합이 높은 쪽에 배팅
        let sum_a: i32 = dice_a.iter().sum();
        let sum_b: i32 = dice_b.iter().sum();
        let group = if sum_a > sum_b { 'A' } else { 'B' };
        // (내 현재 점수 - 상대 현재 점수) / 10을 0이상 100000이하로 잘라서 배팅
        let amount = ((self.my_state.get_total_score() - self.opp_state.get_total_score()) / 10)
            .clamp(0, 100000);
        Bid { group, amount }
    }
    // ============================================================================
    /// 주어진 주사위에 대해 사용할 규칙과 주사위를 정하는 함수
    /// 사용할 규칙과 사용할 주사위의 목록을 pair로 묶어서 반환
    // ============================================================================
    fn calculate_put(&self) -> DicePut {
        // 사용하지 않은 첫 규칙 찾기
        let rule = self
            .my_state
            .rule_score
            .iter()
            .position(|&x| x.is_none())
            .unwrap();
        // 처음 5개 주사위 사용
        let dice_vec: Vec<i32> = self.my_state.dice.iter().take(5).cloned().collect();
        let dice: [i32; 5] = dice_vec.try_into().unwrap();
        DicePut {
            rule: DiceRule::from_usize(rule).unwrap(),
            dice,
        }
    }
    // ============================== [필수 구현 끝] ==============================

    /// 입찰 결과를 받아서 상태 업데이트
    fn update_get(
        &mut self,
        dice_a: &[i32],
        dice_b: &[i32],
        my_bid: &Bid,
        opp_bid: &Bid,
        my_group: char,
    ) {
        // 그룹에 따라 주사위 분배
        if my_group == 'A' {
            self.my_state.add_dice(dice_a);
            self.opp_state.add_dice(dice_b);
        } else {
            self.my_state.add_dice(dice_b);
            self.opp_state.add_dice(dice_a);
        }
        // 입찰 결과에 따른 점수 반영
        let my_bid_ok = my_bid.group == my_group;
        self.my_state.bid(my_bid_ok, my_bid.amount);
        let opp_group = if my_group == 'A' { 'B' } else { 'A' };
        let opp_bid_ok = opp_bid.group == opp_group;
        self.opp_state.bid(opp_bid_ok, opp_bid.amount);
    }
    /// 내가 주사위를 배치한 결과 반영
    fn update_put(&mut self, put: &DicePut) {
        self.my_state.use_dice(put);
    }
    /// 상대가 주사위를 배치한 결과 반영
    fn update_set(&mut self, put: &DicePut) {
        self.opp_state.use_dice(put);
    }
}

impl GameState {
    fn new() -> Self {
        GameState {
            dice: Vec::new(),
            rule_score: [None; 12],
            bid_score: 0,
        }
    }

    /// 현재까지 획득한 총 점수 계산 (상단/하단 점수 + 보너스 + 입찰 점수)
    fn get_total_score(&self) -> i32 {
        let mut basic = 0;
        let mut combination = 0;
        let mut bonus = 0;
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

    /// 주사위 획득
    fn add_dice(&mut self, new_dice: &[i32]) {
        self.dice.extend_from_slice(new_dice);
    }

    /// 주사위 사용
    fn use_dice(&mut self, put: &DicePut) {
        // 이미 사용한 규칙인지 확인
        assert!(
            self.rule_score[put.rule as usize].is_none(),
            "Rule already used"
        );
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
        let dice = &put.dice;
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
                let mut pair = false;
                let mut triple = false;
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
                let e1 = dice.iter().filter(|&&d| d == 1).count() > 0;
                let e2 = dice.iter().filter(|&&d| d == 2).count() > 0;
                let e3 = dice.iter().filter(|&&d| d == 3).count() > 0;
                let e4 = dice.iter().filter(|&&d| d == 4).count() > 0;
                let e5 = dice.iter().filter(|&&d| d == 5).count() > 0;
                let e6 = dice.iter().filter(|&&d| d == 6).count() > 0;
                let ok = (e1 && e2 && e3 && e4) || (e2 && e3 && e4 && e5) || (e3 && e4 && e5 && e6);
                if ok { 15000 } else { 0 }
            }
            DiceRule::LargeStraight => {
                // 5개의 주사위에 적힌 수가 12345, 23456중 하나로 연속되어 있을 때, 30000점, 아닐 경우 0점
                let e1 = dice.iter().filter(|&&d| d == 1).count() > 0;
                let e2 = dice.iter().filter(|&&d| d == 2).count() > 0;
                let e3 = dice.iter().filter(|&&d| d == 3).count() > 0;
                let e4 = dice.iter().filter(|&&d| d == 4).count() > 0;
                let e5 = dice.iter().filter(|&&d| d == 5).count() > 0;
                let e6 = dice.iter().filter(|&&d| d == 6).count() > 0;
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
    fn from(rule: DiceRule) -> Self {
        return rule as usize;
    }
}

impl FromStr for DiceRule {
    type Err = String;

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
    let mut game = Game::new();

    // 입찰 라운드에서 나온 주사위들
    let mut dice_a: Option<[i32; 5]> = None;
    let mut dice_b: Option<[i32; 5]> = None;
    // 내가 마지막으로 한 입찰 정보
    let mut my_bid: Option<Bid> = None;

    for line in stdin.lock().lines() {
        let line = line.unwrap();
        if line.trim().is_empty() {
            continue;
        }

        let parts: Vec<_> = line.split_whitespace().collect();
        let command = parts[0];
        match command {
            "READY" => {
                // 게임 시작
                println!("OK");
                stdout().flush().unwrap();
            }
            "ROLL" => {
                // 주사위 굴리기 결과 받기
                let str_a = parts[1];
                let str_b = parts[2];
                let mut dice_a_array = [0; 5];
                let mut dice_b_array = [0; 5];
                for (dice_val, c) in dice_a_array.iter_mut().zip(str_a.chars()) {
                    *dice_val = c.to_digit(10).unwrap() as i32;
                }
                for (dice_val, c) in dice_b_array.iter_mut().zip(str_b.chars()) {
                    *dice_val = c.to_digit(10).unwrap() as i32;
                }
                dice_a = Some(dice_a_array);
                dice_b = Some(dice_b_array);
                my_bid = Some(game.calculate_bid(&dice_a_array, &dice_b_array));
                let Bid { group, amount } = my_bid.as_ref().unwrap();
                println!("BID {group} {amount}");
                stdout().flush().unwrap();
            }
            "GET" => {
                // 주사위 받기
                let get_group = parts[1].chars().next().unwrap();
                let opp_group = parts[2].chars().next().unwrap();
                let opp_score = parts[3].parse::<i32>().unwrap();
                let my_bid_ref = my_bid.as_ref().unwrap();
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
                // 주사위 골라서 배치하기
                let put = game.calculate_put();
                game.update_put(&put);
                print!("PUT {} ", put.rule);
                for d in &put.dice {
                    print!("{d}");
                }
                println!();
                stdout().flush().unwrap();
            }
            "SET" => {
                // 상대의 주사위 배치
                let rule: DiceRule = parts[1].parse().unwrap();
                let dice_vec: Vec<i32> = parts[2]
                    .chars()
                    .map(|c| c.to_digit(10).unwrap() as i32)
                    .collect();
                let dice: [i32; 5] = dice_vec.try_into().unwrap();
                game.update_set(&DicePut { rule, dice });
            }
            "FINISH" => {
                break;
            }
            _ => {
                // 알 수 없는 명령어 처리
                panic!("Invalid command: {command}");
            }
        }
    }
}
